# Copyright (C) 2009  Lars Wirzenius <liw@liw.fi>
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
import pwd
import stat
import urlparse

# As of 2010-07-10, Debian's paramiko package triggers
# RandomPool_DeprecationWarning. This will eventually be fixed. Until
# then, there is no point in spewing the warning to the user, who can't
# do nothing.
# http://bugs.debian.org/cgi-bin/bugreport.cgi?bug=586925
import warnings
with warnings.catch_warnings():
    warnings.simplefilter('ignore')
    import paramiko

import obnamlib


DEFAULT_SSH_PORT = 22


class SftpFS(obnamlib.VirtualFileSystem):

    '''A VFS implementation for SFTP.
    
    
    
    '''

    def __init__(self, baseurl):
        obnamlib.VirtualFileSystem.__init__(self, baseurl)
        self.sftp = None
        self.reinit(baseurl)
        
    def connect(self):
        self.transport = paramiko.Transport((self.host, self.port))
        self.transport.connect()
        self._check_host_key(self.host)
        self._authenticate(self.user)
        self.sftp = paramiko.SFTPClient.from_transport(self.transport)
        self.chdir(self.path)

    def _check_host_key(self, hostname):
        key = self.transport.get_remote_server_key()
        known_hosts = os.path.expanduser('~/.ssh/known_hosts')
        keys = paramiko.util.load_host_keys(known_hosts)
        if hostname not in keys:
            raise obnamlib.AppException('Host not in known_hosts: %s' % 
                                        hostname)
        elif not keys[hostname].has_key(key.get_name()):
            raise obnamlib.AppException('No host key for %s' % hostname)
        elif keys[hostname][key.get_name()] != key:
            raise obnamlib.AppException('Host key has changed for %s' % 
                                        hostname)
    
    def _authenticate(self, username):
        agent = paramiko.Agent()
        agent_keys = agent.get_keys()
        for key in agent_keys:
            try:
                self.transport.auth_publickey(username, key)
                return
            except paramiko.SSHException:
                pass
        raise obnamlib.AppException('Can\'t authenticate to SSH server '
                                    'using agent.')

    def close(self):
        self.sftp.close()
        self.transport.close()
        self.sftp = None

    def reinit(self, baseurl):
        scheme, netloc, path, query, fragment = urlparse.urlsplit(baseurl)

        if scheme != 'sftp':
            raise obnamlib.Error('SftpFS used with non-sftp URL: %s' % baseurl)

        if '@' in netloc:
            user, netloc = netloc.split('@', 1)
        else:
            user = self._get_username()

        if ':' in netloc:
            host, port = netloc.split(':', 1)
            port = int(port)
        else:
            host = netloc
            port = DEFAULT_SSH_PORT

        if path.startswith('/~/'):
            path = path[3:]

        self.host = host
        self.port = port
        self.user = user
        self.path = path
        
        if self.sftp:
            self.sftp.chdir(path)

    def _get_username(self):
        return pwd.getpwuid(os.getuid()).pw_name

    def getcwd(self):
        return self.sftp.getcwd()

    def chdir(self, pathname):
        try:
            self.sftp.chdir(pathname)
        except IOError, e:
            raise OSError(e.errno, e.strerror, pathname)

    def listdir(self, pathname):
        return self.sftp.listdir(pathname)

    def lock(self, lockname):
        try:
            self.write_file(lockname, '')
        except IOError, e:
            if e.errno == errno.EEXIST:
                raise obnamlib.AppException('Lock %s already exists' % 
                                            lockname)
            else:
                raise

    def unlock(self, lockname):
        if self.exists(lockname):
            self.remove(lockname)

    def exists(self, pathname):
        try:
            self.lstat(pathname)
        except OSError:
            return False
        else:
            return True

    def isdir(self, pathname):
        try:
            st = self.lstat(pathname)
        except OSError:
            return False
        else:
            return stat.S_ISDIR(st.st_mode)

    def mkdir(self, pathname):
        try:
            self.sftp.mkdir(pathname)
        except IOError, e:
            raise OSError(e.errno, e.strerror, pathname)
        
    def makedirs(self, pathname):
        if self.isdir(pathname):
            return
        parent = os.path.dirname(pathname)
        if parent and parent != pathname:
            self.makedirs(parent)
        self.mkdir(pathname)

    def rmdir(self, pathname):
        self.sftp.rmdir(pathname)
        
    def remove(self, pathname):
        self.sftp.remove(pathname)

    def rename(self, old, new):
        self.sftp.rename(old, new)
    
    def lstat(self, pathname):
        try:
            return self.sftp.lstat(pathname)
        except IOError, e:
            raise OSError(e.errno, e.strerror, pathname)

    def chown(self, pathname, uid, gid):
        self.sftp.chown(pathname, uid, gid)
        
    def chmod(self, pathname, mode):
        self.sftp.chmod(pathname, mode)
        
    def lutimes(self, pathname, atime, mtime):
        # FIXME: This does not work for symlinks!
        # Sftp does not have a way of doing that. This means if the restore
        # target is over sftp, symlinks and their targets will have wrong
        # mtimes.
        if getattr(self, 'lutimes_warned', False):
            logging.warning('lutimes used over SFTP, this does not work '
                            'against symlinks (warning appears only first '
                            'time)')
            self.lutimes_warned = True
        self.sftp.utime(pathname, (atime, mtime))

    def link(self, existing_path, new_path):
        raise obnamlib.AppException('Cannot hardlink on SFTP. Sorry.')

    def readlink(self, symlink):
        return self.sftp.readlink(symlink)

    def symlink(self, source, destination):
        self.sftp.symlink(source, destination)

    def open(self, pathname, mode):
        return self.sftp.file(pathname, mode)

    def cat(self, pathname):
        f = self.open(pathname, 'r')
        chunks = []
        while True:
            # 32 KiB is the chunk size that gives me the fastest speed
            # for sftp transfers. I don't know why the size matters.
            chunk = f.read(32 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        f.close()
        return ''.join(chunks)

    def write_file(self, pathname, contents):
        self._write_helper(pathname, 'wx', contents)

    def overwrite_file(self, pathname, contents, make_backup=True):
        self._write_helper(pathname, 'w', contents)

    def _write_helper(self, pathname, mode, contents):
        self.makedirs(pathname)
        f = self.open(pathname, mode)
        chunk_size = 32 * 1024
        for pos in range(0, len(contents), chunk_size):
            chunk = contents[pos:pos + chunk_size]
            f.write(chunk)
        f.close()


class SftpPlugin(obnamlib.ObnamPlugin):

    def enable(self):
        self.app.fsf.register('sftp', SftpFS)

