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


import urlparse

import obnamlib


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
        self.progress = None

    def connect(self):
        """Connect to filesystem."""
        
    def close(self):
        """Close connection to filesystem."""

    def listdir(self, relative_path):
        """Return list of basenames of entities at relative_path."""

    def lock(self, lockname):
        """Create a lock file with the given name."""

    def unlock(self, lockname):
        """Remove a lock file."""

    def exists(self, relative_path):
        """Does the file or directory exist?"""

    def isdir(self, relative_path):
        """Is it a directory?"""

    def mkdir(self, relative_path):
        """Create a directory.
        
        Parent directories must already exist.
        
        """
        
    def makedirs(self, relative_path):
        """Create a directory, and missing parents."""

    def remove(self, relative_path):
        """Remove a file."""

    def lstat(self, relative_path):
        """Like os.lstat."""

    def chmod(self, relative_path, mode):
        """Like os.chmod."""

    def lutimes(self, relative_path, atime, mtime):
        """Like lutimes(2)."""

    def link(self, existing_path, new_path):
        """Like os.link."""

    def readlink(self, symlink):
        """Like os.readlink."""

    def symlink(self, source, destination):
        """Like os.symlink."""

    def open(self, relative_path, mode):
        """Open a file, like the builtin open() or file() function.

        The return value is a file object like the ones returned
        by the builtin open() function.

        """

    def cat(self, relative_path):
        """Return the contents of a file."""

    def write_file(self, relative_path, contents):
        """Write a new file.

        The file must not yet exist. The file is written atomically,
        so that the given name will only exist when the file is
        completely written.
        
        Any directories in relative_path will be created if necessary.

        """

    def overwrite_file(self, relative_path, contents):
        """Like write_file, but overwrites existing file.

        The old file isn't immediately lost, it gets renamed with
        a backup suffix.

        """

    def depth_first(self, relative_path, prune=None):
        """Walk a directory tree depth-first, except for unwanted subdirs.
        
        This is, essentially, 'os.walk(top, topdown=False)', except that
        if the prune argument is set, we call it before descending to 
        sub-directories to allow it to remove any directories and files
        the caller does not want to know about.
        
        If set, prune must be a function that gets three arguments (current
        directory, list of sub-directory names, list of files in directory),
        and must modify the two lists _in_place_. For example:
        
        def prune(dirname, dirnames, filenames):
            if ".bzr" in dirnames:
                dirnames.remove(".bzr")
        
        The dirnames and filenames lists contain basenames, relative to
        dirname.
        
        """
        
        
class VfsFactory:

    """Create new instances of VirtualFileSystem."""
    
    def new(self, url):
        """Create a new VFS appropriate for a given URL."""
        scheme, netloc, path, params, query, fragment = urlparse.urlparse(url)
        if scheme == "sftp":
            return obnamlib.SftpFS(url)
        else:
            return obnamlib.LocalFS(url)
