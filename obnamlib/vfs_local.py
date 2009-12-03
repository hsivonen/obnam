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
import logging
import os
import tempfile

import obnamlib


class LocalFS(obnamlib.VirtualFileSystem):

    """A VFS implementation for local filesystems."""
    
    chunk_size = 1024 * 1024

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

    def lstat(self, relative_path):
        return os.lstat(self.join(relative_path))

    def chown(self, relative_path, uid, gid): # pragma: no cover
        os.chown(self.join(relative_path), uid, gid)

    def chmod(self, relative_path, mode):
        os.chmod(self.join(relative_path), mode)

    def lutimes(self, relative_path, atime, mtime):
        obnamlib._obnam.lutimes(self.join(relative_path), atime, mtime)

    def link(self, existing, new):
        os.link(self.join(existing), self.join(new))

    def readlink(self, relative_path):
        return os.readlink(self.join(relative_path))

    def symlink(self, existing, new):
        os.symlink(existing, self.join(new))

    def open(self, relative_path, mode):
        return file(self.join(relative_path), mode)

    def exists(self, relative_path):
        return os.path.exists(self.join(relative_path))

    def isdir(self, relative_path):
        return os.path.isdir(self.join(relative_path))

    def mkdir(self, relative_path):
        os.mkdir(self.join(relative_path))

    def makedirs(self, relative_path):
        os.makedirs(self.join(relative_path))

    def cat(self, relative_path):
        logging.debug("LocalFS: Reading %s" % relative_path)
        f = self.open(relative_path, "r")
        chunks = []
        while True:
            chunk = f.read(self.chunk_size)
            if not chunk:
                break
            chunks.append(chunk)
#            self.progress["bytes-received"] += len(chunk)
        f.close()
        data = "".join(chunks)
        logging.debug("LocalFS: %s had %d bytes" % (relative_path, len(data)))
        return data

    def write_file(self, relative_path, contents):
        logging.debug("LocalFS: Writing %s (%d)" % 
                      (relative_path, len(contents)))
        path = self.join(relative_path)
        dirname = os.path.dirname(path)
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        fd, name = tempfile.mkstemp(dir=dirname)
        pos = 0
        while pos < len(contents):
            chunk = contents[pos:pos+self.chunk_size]
            os.write(fd, chunk)
#            self.progress["bytes-sent"] += len(chunk)
            pos += len(chunk)
        os.close(fd)
        try:
            os.link(name, path)
        except OSError:
            os.remove(name)
            raise
        os.remove(name)
        logging.debug("LocalFS: write_file updates bytes-sent")

    def overwrite_file(self, relative_path, contents):
        logging.debug("LocalFS: Over-writing %s (%d)" % 
                      (relative_path, len(contents)))
        path = self.join(relative_path)
        dirname = os.path.dirname(path)
        fd, name = tempfile.mkstemp(dir=dirname)
        pos = 0
        while pos < len(contents):
            chunk = contents[pos:pos+self.chunk_size]
            os.write(fd, chunk)
#            self.progress["bytes-sent"] += len(chunk)
            pos += len(chunk)
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

    def listdir(self, dirname):
        return os.listdir(self.join(dirname))
