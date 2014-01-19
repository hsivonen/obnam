# Copyright (C) 2009  Lars Wirzenius
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


import errno
import grp
import logging
import os
import pwd
import stat
import struct
import tracing

import obnamlib


metadata_verify_fields = (
    'st_mode', 'st_mtime_sec', 'st_mtime_nsec',
    'st_nlink', 'st_size', 'st_uid', 'groupname', 'username', 'target',
    'xattr',
)
metadata_fields = metadata_verify_fields + (
    'st_blocks', 'st_dev', 'st_gid', 'st_ino',  'st_atime_sec',
    'st_atime_nsec', 'md5',
)


class Metadata(object):

    '''Represent metadata for a filesystem entry.

    The metadata for a filesystem entry (file, directory, device, ...)
    consists of its stat(2) result, plus ACL and xattr.

    This class represents them as fields.

    We do not store all stat(2) fields. Here's a commentary on all fields:

        field?          stored? why

        st_atime_sec    yes     mutt compares atime, mtime to see ifmsg is new
        st_atime_nsec   yes     mutt compares atime, mtime to see ifmsg is new
        st_blksize      no      no way to restore, not useful backed up
        st_blocks       yes     should restore create holes in file?
        st_ctime        no      no way to restore, not useful backed up
        st_dev          yes     used to restore hardlinks
        st_gid          yes     used to restore group ownership
        st_ino          yes     used to restore hardlinks
        st_mode         yes     used to restore permissions
        st_mtime_sec    yes     used to restore mtime
        st_mtime_nsec   yes     used to restore mtime
        st_nlink        yes     used to restore hardlinks
        st_rdev         no      no use (correct me if I'm wrong about this)
        st_size         yes     user needs it to see size of file in backup
        st_uid          yes     used to restored ownership

    The field 'target' stores the target of a symlink.

    Additionally, the fields 'groupname' and 'username' are stored. They
    contain the textual names that correspond to st_gid and st_uid. When
    restoring, the names will be preferred by default.

    The 'md5' field optionally stores the whole-file checksum for the file.

    The 'xattr' field optionally stores extended attributes encoded as
    a binary blob.

    '''

    def __init__(self, **kwargs):
        for field in metadata_fields:
            setattr(self, field, None)
        for field, value in kwargs.iteritems():
            setattr(self, field, value)

    def isdir(self):
        return self.st_mode is not None and stat.S_ISDIR(self.st_mode)

    def islink(self):
        return self.st_mode is not None and stat.S_ISLNK(self.st_mode)

    def isfile(self):
        return self.st_mode is not None and stat.S_ISREG(self.st_mode)

    def __repr__(self): # pragma: no cover
        fields = ', '.join('%s=%s' % (k, getattr(self, k))
                           for k in metadata_fields)
        return 'Metadata(%s)' % fields

    def __cmp__(self, other):
        for field in metadata_fields:
            ours = getattr(self, field)
            theirs = getattr(other, field)
            if ours == theirs:
                continue
            if ours < theirs:
                return -1
            if ours > theirs:
                return +1
        return 0


# Caching versions of username/groupname lookups.
# These work on the assumption that the mappings from uid/gid do not
# change during the runtime of the backup.

_uid_to_username = {}
def _cached_getpwuid(uid): # pragma: no cover
    if uid not in _uid_to_username:
        _uid_to_username[uid] = pwd.getpwuid(uid)
    return _uid_to_username[uid]

_gid_to_groupname = {}
def _cached_getgrgid(gid): # pragma: no cover
    if gid not in _gid_to_groupname:
        _gid_to_groupname[gid] = grp.getgrgid(gid)
    return _gid_to_groupname[gid]


def get_xattrs_as_blob(fs, filename): # pragma: no cover
    tracing.trace('filename=%s' % filename)

    try:
        names = fs.llistxattr(filename)
    except (OSError, IOError), e:
        if e.errno in (errno.EOPNOTSUPP, errno.EACCES):
            return None
        raise
    tracing.trace('names=%s' % repr(names))
    if not names:
        return None

    values = []
    for name in names[:]:
        tracing.trace('trying name %s' % repr(name))
        try:
            value = fs.lgetxattr(filename, name)
        except OSError, e:
            # On btrfs, at least, this can happen: the filesystem returns
            # a list of attribute names, but then fails when looking up
            # the value for one or more of the names. We pretend that the
            # name was never returned in that case.
            #
            # Obviously this can happen due to race conditions as well.
            if e.errno == errno.ENODATA:
                names.remove(name)
                logging.warning(
                    '%s has extended attribute named %s without value, '
                    'ignoring attribute' % (filename, name))
            else:
                raise
        else:
            tracing.trace('lgetxattr(%s)=%s' % (name, value))
            values.append(value)
    assert len(names) == len(values)

    name_blob = ''.join('%s\0' % name for name in names)

    lengths = [len(v) for v in values]
    fmt = '!' + 'Q' * len(values)
    value_blob = struct.pack(fmt, *lengths) + ''.join(values)

    return ('%s%s%s' %
            (struct.pack('!Q', len(name_blob)),
             name_blob,
             value_blob))


def set_xattrs_from_blob(fs, filename, blob): # pragma: no cover
    sizesize = struct.calcsize('!Q')
    name_blob_size = struct.unpack('!Q', blob[:sizesize])[0]
    name_blob = blob[sizesize : sizesize + name_blob_size]
    value_blob = blob[sizesize + name_blob_size : ]

    names = [s for s in name_blob.split('\0')[:-1]]
    fmt = '!' + 'Q' * len(names)
    lengths_size = sizesize * len(names)
    lengths = struct.unpack(fmt, value_blob[:lengths_size])

    pos = lengths_size
    for i, name in enumerate(names):
        value = value_blob[pos:pos + lengths[i]]
        pos += lengths[i]
        fs.lsetxattr(filename, name, value)


def read_metadata(fs, filename, st=None, getpwuid=None, getgrgid=None):
    '''Return object detailing metadata for a filesystem entry.'''
    metadata = Metadata()
    stat_result = st or fs.lstat(filename)
    for field in metadata_fields:
        if field.startswith('st_') and hasattr(stat_result, field):
            setattr(metadata, field, getattr(stat_result, field))

    if stat.S_ISLNK(stat_result.st_mode):
        metadata.target = fs.readlink(filename)
    else:
        metadata.target = ''

    getgrgid = getgrgid or _cached_getgrgid
    try:
        metadata.groupname = getgrgid(metadata.st_gid)[0]
    except KeyError:
        metadata.groupname = None

    getpwuid = getpwuid or _cached_getpwuid
    try:
        metadata.username = getpwuid(metadata.st_uid)[0]
    except KeyError:
        metadata.username = None

    metadata.xattr = get_xattrs_as_blob(fs, filename)

    return metadata


def set_metadata(fs, filename, metadata, 
                 getuid=None, always_set_id_bits=False):
    '''Set metadata for a filesystem entry.

    We only set metadata that can sensibly be set: st_atime, st_mode,
    st_mtime. We also attempt to set ownership (st_gid, st_uid), but
    only if we're running as root. We ignore the username, groupname
    fields: we assume the caller will change st_uid, st_gid accordingly
    if they want to mess with things. This makes the user take care
    of error situations and looking up user preferences.

    '''

    symlink = stat.S_ISLNK(metadata.st_mode)
    if symlink:
        fs.symlink(metadata.target, filename)

    # Set owner before mode, so that a setuid bit does not get reset.
    getuid = getuid or os.getuid
    if getuid() == 0:
        fs.lchown(filename, metadata.st_uid, metadata.st_gid)

    # If we are not the owner, and not root, do not restore setuid/setgid,
    # unless explicitly told to do so.
    mode = metadata.st_mode
    set_id_bits = always_set_id_bits or (getuid() in (0, metadata.st_uid))
    if not set_id_bits: # pragma: no cover
        mode = mode & (~stat.S_ISUID)
        mode = mode & (~stat.S_ISGID)
    if symlink:
        fs.chmod_symlink(filename, mode)
    else:
        fs.chmod_not_symlink(filename, mode)

    if metadata.xattr: # pragma: no cover
        set_xattrs_from_blob(fs, filename, metadata.xattr)

    fs.lutimes(filename, metadata.st_atime_sec, metadata.st_atime_nsec,
               metadata.st_mtime_sec, metadata.st_mtime_nsec)


metadata_format = struct.Struct('!Q' +  # flags
                                'Q' +   # st_mode
                                'qQ' +  # st_mtime_sec and _nsec
                                'qQ' +  # st_atime_sec and _nsec
                                'Q' +   # st_nlink
                                'Q' +   # st_size
                                'Q' +   # st_uid
                                'Q' +   # st_gid
                                'Q' +   # st_dev
                                'Q' +   # st_ino
                                'Q' +   # st_blocks
                                'Q' +   # len of groupname
                                'Q' +   # len of username
                                'Q' +   # len of symlink target
                                'Q' +   # len of md5
                                'Q' +   # len of xattr
                                '')

def encode_metadata(metadata):
    flags = 0
    for i, name in enumerate(obnamlib.metadata_fields):
        if getattr(metadata, name) is not None:
            flags |= (1 << i)

    try:
        packed = metadata_format.pack(flags,
                                      metadata.st_mode or 0,
                                      metadata.st_mtime_sec or 0,
                                      metadata.st_mtime_nsec or 0,
                                      metadata.st_atime_sec or 0,
                                      metadata.st_atime_nsec or 0,
                                      metadata.st_nlink or 0,
                                      metadata.st_size or 0,
                                      metadata.st_uid or 0,
                                      metadata.st_gid or 0,
                                      metadata.st_dev or 0,
                                      metadata.st_ino or 0,
                                      metadata.st_blocks or 0,
                                      len(metadata.groupname or ''),
                                      len(metadata.username or ''),
                                      len(metadata.target or ''),
                                      len(metadata.md5 or ''),
                                      len(metadata.xattr or ''))
    except TypeError, e: # pragma: no cover
        logging.error('ERROR: Packing error due to %s' % str(e))
        logging.error('ERROR: st_mode=%s' % repr(metadata.st_mode))
        logging.error('ERROR: st_mtime_sec=%s' % repr(metadata.st_mtime_sec))
        logging.error('ERROR: st_mtime_nsec=%s' % repr(metadata.st_mtime_nsec))
        logging.error('ERROR: st_atime_sec=%s' % repr(metadata.st_atime_sec))
        logging.error('ERROR: st_atime_nsec=%s' % repr(metadata.st_atime_nsec))
        logging.error('ERROR: st_nlink=%s' % repr(metadata.st_nlink))
        logging.error('ERROR: st_size=%s' % repr(metadata.st_size))
        logging.error('ERROR: st_uid=%s' % repr(metadata.st_uid))
        logging.error('ERROR: st_gid=%s' % repr(metadata.st_gid))
        logging.error('ERROR: st_dev=%s' % repr(metadata.st_dev))
        logging.error('ERROR: st_ino=%s' % repr(metadata.st_ino))
        logging.error('ERROR: st_blocks=%s' % repr(metadata.st_blocks))
        logging.error('ERROR: groupname=%s' % repr(metadata.groupname))
        logging.error('ERROR: username=%s' % repr(metadata.username))
        logging.error('ERROR: target=%s' % repr(metadata.target))
        logging.error('ERROR: md5=%s' % repr(metadata.md5))
        logging.error('ERROR: xattr=%s' % repr(metadata.xattr))
        raise
    return (packed +
             (metadata.groupname or '') +
             (metadata.username or '') +
             (metadata.target or '') +
             (metadata.md5 or '') +
             (metadata.xattr or ''))


def decode_metadata(encoded):

    items = metadata_format.unpack_from(encoded)
    flags = items[0]
    pos = [1, metadata_format.size]
    metadata = obnamlib.Metadata()

    def is_present(field):
        i = obnamlib.metadata_fields.index(field)
        return (flags & (1 << i)) != 0

    def decode(field, num_items, inc_offset, getvalue):
        if is_present(field):
            value = getvalue(pos[0], pos[1])
            setattr(metadata, field, value)
            if inc_offset:
                pos[1] += len(value)
        pos[0] += num_items

    def decode_integer(field):
        decode(field, 1, False, lambda i, o: items[i])

    def decode_string(field):
        decode(field, 1, True, lambda i, o: encoded[o:o + items[i]])

    decode_integer('st_mode')
    decode_integer('st_mtime_sec')
    decode_integer('st_mtime_nsec')
    decode_integer('st_atime_sec')
    decode_integer('st_atime_nsec')
    decode_integer('st_nlink')
    decode_integer('st_size')
    decode_integer('st_uid')
    decode_integer('st_gid')
    decode_integer('st_dev')
    decode_integer('st_ino')
    decode_integer('st_blocks')
    decode_string('groupname')
    decode_string('username')
    decode_string('target')
    decode_string('md5')
    decode_string('xattr')

    return metadata

