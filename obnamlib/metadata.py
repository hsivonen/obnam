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


import grp
import os
import pwd
import stat
import struct

import obnamlib


metadata_verify_fields = (
    'st_mode', 'st_mtime', 'st_nlink', 'st_size', 'st_uid', 
    'groupname', 'username', 'target',
)
metadata_fields = metadata_verify_fields + (
    'st_blocks', 'st_dev', 'st_gid', 'st_ino',  'st_atime', 'md5',
)


class Metadata(object):

    '''Represent metadata for a filesystem entry.
    
    The metadata for a filesystem entry (file, directory, device, ...)
    consists of its stat(2) result, plus ACL and xattr.
    
    This class represents them as fields.
    
    We do not store all stat(2) fields. Here's a commentary on all fields:
    
        field?      stored? why
    
        st_atime    yes     mutt compars atime with mtime to see if msg is new
        st_blksize  no      no way to restore, not useful backed up
        st_blocks   yes     used to see if restore should create holes in file
        st_ctime    no      no way to restore, not useful backed up
        st_dev      yes     used to restore hardlinks
        st_gid      yes     used to restore group ownership
        st_ino      yes     used to restore hardlinks
        st_mode     yes     used to restore permissions
        st_mtime    yes     used to restore mtime
        st_nlink    yes     used to restore hardlinks
        st_rdev     no      no use (correct me if I'm wrong about this)
        st_size     yes     user needs it to see size of file in backup
        st_uid      yes     used to restored ownership

    The field 'target' stores the target of a symlink.
        
    Additionally, the fields 'groupname' and 'username' are stored. They
    contain the textual names that correspond to st_gid and st_uid. When
    restoring, the names will be preferred by default.
    
    The 'md5' field optionally stores the whole-file checksum for the file.
    
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


def read_metadata(fs, filename, getpwuid=None, getgrgid=None):
    '''Return object detailing metadata for a filesystem entry.'''
    metadata = Metadata()
    stat_result = fs.lstat(filename)
    for field in metadata_fields:
        if field.startswith('st_'):
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

    return metadata


def set_metadata(fs, filename, metadata, getuid=None):
    '''Set metadata for a filesystem entry.

    We only set metadata that can sensibly be set: st_atime, st_mode,
    st_mtime. We also attempt to set ownership (st_gid, st_uid), but
    only if we're running as root. We ignore the username, groupname
    fields: we assume the caller will change st_uid, st_gid accordingly
    if they want to mess with things. This makes the user take care
    of error situations and looking up user preferences.
    
    '''

    if stat.S_ISLNK(metadata.st_mode):
        fs.symlink(metadata.target, filename)
    else:
        fs.chmod(filename, metadata.st_mode)
    fs.lutimes(filename, metadata.st_atime, metadata.st_mtime)

    getuid = getuid or os.getuid
    if getuid() == 0:
        fs.lchown(filename, metadata.st_uid, metadata.st_gid)
    
    
metadata_format = struct.Struct('!Q' +  # flags
                                'Q' +   # st_mode
                                'QQ' +  # st_mtime (as two integers)
                                'QQ' +  # st_atime (as two integers)
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
                                '')

def encode_metadata(metadata):
    flags = 0
    for i, name in enumerate(obnamlib.metadata_fields):
        if getattr(metadata, name) is not None:
            flags |= (1 << i)

    if metadata.st_mtime is None:
        mtime_a, mtime_b = 0, 0
    else:
        mtime_a, mtime_b = metadata.st_mtime.as_integer_ratio()
    if metadata.st_atime is None:
        atime_a, atime_b = 0, 0
    else:
        atime_a, atime_b = metadata.st_atime.as_integer_ratio()
    packed = metadata_format.pack(flags,
                                  metadata.st_mode or 0,
                                  mtime_a, mtime_b,
                                  atime_a, atime_b,
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
                                  len(metadata.md5 or ''))
    return (packed + 
             (metadata.groupname or '') +
             (metadata.username or '') +
             (metadata.target or '') +
             (metadata.md5 or ''))

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

    def decode_float(field):
        decode(field, 2, False, lambda i, o: float(items[i]) / items[i+1])

    def decode_string(field):
        decode(field, 1, True, lambda i, o: encoded[o:o + items[i]])
    
    decode_integer('st_mode')
    decode_float('st_mtime')
    decode_float('st_atime')
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
    
    return metadata

