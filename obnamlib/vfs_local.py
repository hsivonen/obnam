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
    
    def __init__(self, baseurl):
        obnamlib.VirtualFileSystem.__init__(self, baseurl)
        self.reinit(baseurl)

    def reinit(self, baseurl):
        # We fake chdir so that it doesn't mess with the caller's 
        # perception of current working directory. This also benefits
        # unit tests. To do this, we store the baseurl as the cwd.
        self.cwd = os.path.abspath(baseurl)

    def close(self):
        logging.info('VFS %s closing down; bytes_read=%d bytes_written=%d' %
                     (self.baseurl, self.bytes_read, self.bytes_written))

    def getcwd(self):
        return self.cwd

    def chdir(self, pathname):
        newcwd = os.path.abspath(self.join(pathname))
        if not os.path.isdir(newcwd):
            raise OSError('%s is not a directory' % newcwd)
        self.cwd = newcwd

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

    def join(self, pathname):
        return os.path.join(self.cwd, pathname)

    def remove(self, pathname):
        os.remove(self.join(pathname))

    def rename(self, old, new):
        os.rename(self.join(old), self.join(new))

    def lstat(self, pathname):
        return os.lstat(self.join(pathname))

    def chown(self, pathname, uid, gid): # pragma: no cover
        os.chown(self.join(pathname), uid, gid)

    def chmod(self, pathname, mode):
        os.chmod(self.join(pathname), mode)

    def lutimes(self, pathname, atime, mtime):
        ret = obnamlib._obnam.lutimes(self.join(pathname), atime, mtime)
        if ret != 0:
            raise OSError(ret, errno.errorcode[ret], pathname)

    def link(self, existing, new):
        os.link(self.join(existing), self.join(new))

    def readlink(self, pathname):
        return os.readlink(self.join(pathname))

    def symlink(self, existing, new):
        os.symlink(existing, self.join(new))

    def open(self, pathname, mode):
        return file(self.join(pathname), mode)

    def exists(self, pathname):
        return os.path.exists(self.join(pathname))

    def isdir(self, pathname):
        return os.path.isdir(self.join(pathname))

    def mkdir(self, pathname):
        os.mkdir(self.join(pathname))

    def makedirs(self, pathname):
        os.makedirs(self.join(pathname))

    def rmdir(self, pathname):
        os.rmdir(self.join(pathname))

    def cat(self, pathname, osopen=os.open):
        pathname = self.join(pathname)
        try:
            fd = osopen(pathname, os.O_RDONLY)
        except OSError, e:
            if e.errno == errno.ENOENT:
                raise IOError(e.errno, e.strerror, pathname)
            else:
                raise # pragma: no cover
        chunks = []
        offset = 0
        while True:
            chunk = os.read(fd, self.chunk_size)
            if not chunk:
                break
            obnamlib._obnam.fadvise_dontneed(fd, offset, len(chunk))
            offset += len(chunk)
            chunks.append(chunk)
            self.bytes_read += len(chunk)
        os.close(fd)
        data = ''.join(chunks)
        return data

    def write_file(self, pathname, contents):
        path = self.join(pathname)
        dirname = os.path.dirname(path)
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        fd, name = tempfile.mkstemp(dir=dirname)
        pos = 0
        while pos < len(contents):
            chunk = contents[pos:pos+self.chunk_size]
            os.write(fd, chunk)
            pos += len(chunk)
            self.bytes_written += len(chunk)
        os.close(fd)
        try:
            os.link(name, path)
        except OSError:
            os.remove(name)
            raise
        os.remove(name)

    def overwrite_file(self, pathname, contents, make_backup=True):
        path = self.join(pathname)
        dirname = os.path.dirname(path)
        fd, name = tempfile.mkstemp(dir=dirname)
        pos = 0
        while pos < len(contents):
            chunk = contents[pos:pos+self.chunk_size]
            os.write(fd, chunk)
            pos += len(chunk)
            self.bytes_written += len(chunk)
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
        if not make_backup:
            try:
                os.remove(bak)
            except OSError:
                pass

    def listdir(self, dirname):
        return os.listdir(self.join(dirname))
