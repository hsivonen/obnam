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


metadata_verify_fields = (
    'st_mode', 'st_mtime', 'st_nlink', 'st_size', 'st_uid', 
    'groupname', 'username', 'target',
)
metadata_fields = metadata_verify_fields + (
    'st_blocks', 'st_dev', 'st_gid', 'st_ino',  'st_atime', 
    'chunks', 'chunk_groups',
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
    
    Further, the fields 'chunks' and 'chunk_groups' are used internally
    to store a list of chunks (or chunk groups) which relate to this
    file. They are non-None only for regular files and symlinks.
    
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


def read_metadata(fs, filename, getpwuid=None, getgrgid=None):
    '''Return object detailing metadata for a filesystem entry.'''
    metadata = Metadata()
    stat_result = fs.lstat(filename)
    for field in metadata_fields:
        if field.startswith('st_'):
            setattr(metadata, field, int(getattr(stat_result, field)))

    if stat.S_ISLNK(stat_result.st_mode):
        metadata.target = fs.readlink(filename)
    else:
        metadata.target = ''

    getgrgid = getgrgid or grp.getgrgid
    try:
        metadata.groupname = getgrgid(metadata.st_gid)[0]
    except KeyError:
        metadata.groupname = None

    getpwuid = getpwuid or pwd.getpwuid
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
        fs.chown(filename, metadata.st_uid, metadata.st_gid)

