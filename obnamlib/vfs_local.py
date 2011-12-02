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
import fcntl
import logging
import math
import os
import tempfile
import tracing

import obnamlib


class LocalFSFile(file):

    def read(self, amount=-1):
        offset = self.tell()
        data = file.read(self, amount)
        if data:
            fd = self.fileno()
            obnamlib._obnam.fadvise_dontneed(fd, offset, len(data))
        return data

    def write(self, data):
        offset = self.tell()
        file.write(self, data)
        fd = self.fileno()
        obnamlib._obnam.fadvise_dontneed(fd, offset, len(data))


class LocalFS(obnamlib.VirtualFileSystem):

    """A VFS implementation for local filesystems."""
    
    chunk_size = 1024 * 1024
    
    def __init__(self, baseurl, create=False):
        tracing.trace('baseurl=%s', baseurl)
        tracing.trace('create=%s', create)
        obnamlib.VirtualFileSystem.__init__(self, baseurl)
        self.reinit(baseurl, create=create)

    def reinit(self, baseurl, create=False):
        # We fake chdir so that it doesn't mess with the caller's 
        # perception of current working directory. This also benefits
        # unit tests. To do this, we store the baseurl as the cwd.
        tracing.trace('baseurl=%s', baseurl)
        tracing.trace('create=%s', create)
        self.cwd = os.path.abspath(baseurl)
        if not self.isdir('.'):
            if create:
                tracing.trace('creating %s', baseurl)
                os.mkdir(baseurl)
            else:
                raise OSError(errno.ENOENT, self.cwd)

    def getcwd(self):
        return self.cwd

    def chdir(self, pathname):
        tracing.trace('LocalFS(%s).chdir(%s)', self.baseurl, pathname)
        newcwd = os.path.abspath(self.join(pathname))
        if not os.path.isdir(newcwd):
            raise OSError('%s is not a directory' % newcwd)
        self.cwd = newcwd

    def lock(self, lockname):
        tracing.trace('lockname=%s', lockname)
        try:
            self.write_file(lockname, "")
        except OSError, e:
            if e.errno == errno.EEXIST:
                raise obnamlib.Error("Lock %s already exists" % lockname)
            else:
                raise

    def unlock(self, lockname):
        tracing.trace('lockname=%s', lockname)
        if self.exists(lockname):
            self.remove(lockname)

    def join(self, pathname):
        return os.path.join(self.cwd, pathname)

    def remove(self, pathname):
        tracing.trace('remove %s', pathname)
        os.remove(self.join(pathname))

    def rename(self, old, new):
        tracing.trace('rename %s %s', old, new)
        os.rename(self.join(old), self.join(new))

    def lstat(self, pathname):
        (ret, dev, ino, mode, nlink, uid, gid, rdev, size, blksize, blocks,
         atime_sec, atime_nsec, mtime_sec, mtime_nsec, 
         ctime_sec, ctime_nsec) = obnamlib._obnam.lstat(self.join(pathname))
        if ret != 0:
            raise OSError((ret, os.strerror(ret), pathname))
        return obnamlib.Metadata(
                    st_dev=dev,
                    st_ino=ino,
                    st_mode=mode,
                    st_nlink=nlink,
                    st_uid=uid,
                    st_gid=gid,
                    st_rdev=rdev,
                    st_size=size,
                    st_blksize=blksize,
                    st_blocks=blocks,
                    st_atime_sec=atime_sec,
                    st_atime_nsec=atime_nsec,
                    st_mtime_sec=mtime_sec,
                    st_mtime_nsec=mtime_nsec,
                    st_ctime_sec=ctime_sec,
                    st_ctime_nsec=ctime_nsec
                )

    def llistxattr(self, filename): # pragma: no cover
        ret = obnamlib._obnam.llistxattr(self.join(filename))
        if type(ret) is int:
            raise OSError((ret, os.strerror(ret), filename))
        return [s for s in ret.split('\0') if s]

    def lgetxattr(self, filename, attrname): # pragma: no cover
        ret = obnamlib._obnam.lgetxattr(self.join(filename), attrname)
        if type(ret) is int:
            raise OSError((ret, os.strerror(ret), filename))
        return ret

    def lsetxattr(self, filename, attrname, attrvalue): # pragma: no cover
        ret = obnamlib._obnam.lsetxattr(self.join(filename), 
                                        attrname, attrvalue)
        if ret != 0:
            raise OSError((ret, os.strerror(ret), filename))

    def lchown(self, pathname, uid, gid): # pragma: no cover
        tracing.trace('lchown %s %d %d', pathname, uid, gid)
        os.lchown(self.join(pathname), uid, gid)

    def chmod(self, pathname, mode):
        tracing.trace('chmod %s %o', pathname, mode)
        os.chmod(self.join(pathname), mode)

    def lutimes(self, pathname, atime_sec, atime_nsec, mtime_sec, mtime_nsec):
        assert atime_sec is not None
        assert atime_nsec is not None
        assert mtime_sec is not None
        assert mtime_nsec is not None
        ret = obnamlib._obnam.lutimes(self.join(pathname), 
                                      atime_sec, int(atime_nsec / 1000), 
                                      mtime_sec, int(mtime_nsec / 1000))
        if ret != 0:
            raise OSError(ret, os.strerror(ret), pathname)

    def link(self, existing, new):
        tracing.trace('existing=%s', existing)
        tracing.trace('new=%s', new)
        os.link(self.join(existing), self.join(new))

    def readlink(self, pathname):
        return os.readlink(self.join(pathname))

    def symlink(self, existing, new):
        tracing.trace('existing=%s', existing)
        tracing.trace('new=%s', new)
        os.symlink(existing, self.join(new))

    def open(self, pathname, mode):
        tracing.trace('pathname=%s', pathname)
        tracing.trace('mode=%s', mode)
        f = LocalFSFile(self.join(pathname), mode)
        try:
            flags = fcntl.fcntl(f.fileno(), fcntl.F_GETFL)
            flags |= os.O_NOATIME
            fcntl.fcntl(f.fileno(), fcntl.F_SETFL, flags)
        except IOError, e: # pragma: no cover
            tracing.trace('fcntl F_SETFL failed: %s', repr(e))
            return f # ignore any problems setting flags
        return f

    def exists(self, pathname):
        return os.path.exists(self.join(pathname))

    def isdir(self, pathname):
        return os.path.isdir(self.join(pathname))

    def mknod(self, pathname, mode):
        tracing.trace('pathmame=%s', pathname)
        tracing.trace('mode=%o', mode)
        os.mknod(self.join(pathname), mode)

    def mkdir(self, pathname):
        tracing.trace('mkdir %s', pathname)
        os.mkdir(self.join(pathname))

    def makedirs(self, pathname):
        tracing.trace('makedirs %s', pathname)
        os.makedirs(self.join(pathname))

    def rmdir(self, pathname):
        tracing.trace('rmdir %s', pathname)
        os.rmdir(self.join(pathname))

    def cat(self, pathname):
        pathname = self.join(pathname)
        f = self.open(pathname, 'rb')
        chunks = []
        while True:
            chunk = f.read(self.chunk_size)
            if not chunk:
                break
            chunks.append(chunk)
            self.bytes_read += len(chunk)
        f.close()
        data = ''.join(chunks)
        return data

    def write_file(self, pathname, contents):
        tracing.trace('write_file %s', pathname)
        tempname = self._write_to_tempfile(pathname, contents)
        path = self.join(pathname)
        try:
            os.link(tempname, path)
        except OSError:
            os.remove(tempname)
            raise
        os.remove(tempname)

    def overwrite_file(self, pathname, contents, make_backup=True):
        tracing.trace('overwrite_file %s', pathname)
        tempname = self._write_to_tempfile(pathname, contents)
        path = self.join(pathname)

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
        os.rename(tempname, path)
        if not make_backup:
            try:
                os.remove(bak)
            except OSError:
                pass
                
    def _write_to_tempfile(self, pathname, contents):
        path = self.join(pathname)
        dirname = os.path.dirname(path)
        if not os.path.exists(dirname):
            os.makedirs(dirname)

        fd, tempname = tempfile.mkstemp(dir=dirname)
        os.close(fd)
        f = self.open(tempname, 'wb')

        pos = 0
        while pos < len(contents):
            chunk = contents[pos:pos+self.chunk_size]
            f.write(chunk)
            pos += len(chunk)
            self.bytes_written += len(chunk)
        f.close()
        return tempname

    def listdir(self, dirname):
        return os.listdir(self.join(dirname))

    def listdir2(self, dirname):
        return [(name, self.lstat(os.path.join(dirname, name)))
                 for name in os.listdir(self.join(dirname))]

