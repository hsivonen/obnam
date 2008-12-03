# Copyright (C) 2008  Lars Wirzenius <liw@liw.fi>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.


class VirtualFileSystem(object):

    """A virtual filesystem interface.
    
    The backup program needs to access both local and remote files.
    To make it easier to support all kinds of files both locally and
    remotely, we use a custom virtual filesystem interface so that
    all filesystem access is done the same way. This way, we can
    easily support user data and backup stores in any combination of
    local and remote filesystems.

    This class defines the interface for such virtual filesystems.
    Sub-classes will actually implement the interface.

    When a VFS is instantiated, it is bound to a base URL. When
    accessing the virtual filesystem, all paths are then given
    relative to the base URL. The Unix syntax for files is used
    for the relative paths: directory components separated by
    slashes, and an initial slash indicating the root of the
    filesystem (in this case, the base URL).

    """

    def __init__(self, baseurl):
        self.baseurl = baseurl

    def lock(self, lockname):
        """Create a lock file with the given name."""
        pass

    def unlock(self, lockname):
        """Remove a lock file."""
        pass

    def exists(self, relative_path):
        """Does the file or directory exist?"""
        pass

    def remove(self, relative_path):
        """Remove a file."""
        pass

    def open(self, relative_path, mode):
        """Open a file, like the builtin open() or file() function.

        The return value is a file object like the ones returned
        by the builtin open() function.

        """
        pass

    def cat(self, relative_path):
        """Return the contents of a file."""
        pass

    def write_file(self, relative_path, contents):
        """Write a new file.

        The file must not yet exist. The file is written atomically,
        so that the given name will only exist when the file is
        completely written.

        """
        pass
