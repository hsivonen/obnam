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


import errno
import os
import tempfile

import obnamlib


class LocalFS(obnamlib.VirtualFileSystem):

    """A VFS implementation for local filesystems."""

    def lock(self, lockname):
        try:
            self.write_file(lockname, "")
        except OSError, e:
            if e.errno == errno.EEXIST:
                raise obnamlib.Exception("Lock %s already exists" % lockname)
            else:
                raise

    def unlock(self, lockname):
        if self.exists(lockname):
            self.remove(lockname)

    def join(self, relative_path):
        return os.path.join(self.baseurl, relative_path.lstrip("/"))

    def remove(self, relative_path):
        os.remove(self.join(relative_path))

    def open(self, relative_path, mode):
        return file(self.join(relative_path), mode)

    def exists(self, relative_path):
        return os.path.exists(self.join(relative_path))

    def isdir(self, relative_path):
        return os.path.isdir(self.join(relative_path))

    def cat(self, relative_path):
        f = self.open(relative_path, "r")
        data = f.read()
        f.close()
        return data

    def write_file(self, relative_path, contents):
        path = self.join(relative_path)
        dirname = os.path.dirname(path)
        fd, name = tempfile.mkstemp(dir=dirname)
        os.write(fd, contents)
        os.close(fd)
        try:
            os.link(name, path)
        except OSError:
            os.remove(name)
            raise
        os.remove(name)

    def overwrite_file(self, relative_path, contents):
        path = self.join(relative_path)
        dirname = os.path.dirname(path)
        fd, name = tempfile.mkstemp(dir=dirname)
        os.write(fd, contents)
        os.close(fd)

        # Rename existing to have a .bak suffix. If _that_ file already
        # exists, remove that.
        bak = path + ".bak"
        try:
            os.remove(bak)
        except OSError:
            pass
        try:
            os.link(path, bak)
        except OSError:
            pass
        os.rename(name, path)

    def depth_first(self, top, prune=None):
        # We walk topdown, since that's the only way os.walk allows us to
        # do any pruning. We use os.walk to get the exact same error handling
        # and other logic it uses.
        for dirname, dirnames, filenames in os.walk(top):

            # Prune. This modifies dirnames and filenames in place.
            if prune:
                prune(dirname, dirnames, filenames)

            # Make a duplicate of the dirnames, then empty the existing list.
            # This way, os.walk won't try to walk to subdirectories. We'll
            # do that manually.
            real_dirnames = dirnames[:]
            del dirnames[:]

            # Process subdirectories, recursively.
            for subdirname in real_dirnames:
                subdirpath = os.path.join(dirname, subdirname)
                for x in self.depth_first(subdirpath, prune=prune):
                    yield x

            # Return current directory last.
            yield dirname, real_dirnames, filenames
