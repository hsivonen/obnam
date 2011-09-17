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
import hashlib
import logging
import os
import pwd
import random
import socket
import stat
import subprocess
import time
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


def ioerror_to_oserror(method):
    '''Decorator to convert an IOError exception to OSError.
    
    Python's os.* raise OSError, mostly, but paramiko's corresponding
    methods raise IOError. This decorator fixes that.
    
    '''
    
    def helper(self, filename, *args, **kwargs):
        try:
            return method(self, filename, *args, **kwargs)
        except IOError, e:
            raise OSError(e.errno, e.strerror, filename)
    
    return helper


class SSHChannelAdapter(object):

    '''Take an ssh subprocess and pretend it is a paramiko Channel.'''
    
    # This is inspired by the ssh.py module in bzrlib.

    def __init__(self, proc):
        self.proc = proc

    def send(self, data):
        return os.write(self.proc.stdin.fileno(), data)

    def recv(self, count):
        try:
            return os.read(self.proc.stdout.fileno(), count)
        except socket.error, e:
            if e.args[0] in (errno.EPIPE, errno.ECONNRESET, errno.ECONNABORTED,
                             errno.EBADF):
                # Connection has closed.  Paramiko expects an empty string in
                # this case, not an exception.
                return ''
            raise

    def get_name(self):
        return 'obnam SSHChannelAdapter'

    def close(self):
        for func in [self.proc.stdin.close, self.proc.stdout.close, 
                     self.proc.wait]:
            try:
                func()
            except OSError:
                pass


class SftpFS(obnamlib.VirtualFileSystem):

    '''A VFS implementation for SFTP.
    
    
    
    '''
    
    # 32 KiB is the chunk size that gives me the fastest speed
    # for sftp transfers. I don't know why the size matters.
    chunk_size = 32 * 1024

    def __init__(self, baseurl, create=False, settings=None):
        obnamlib.VirtualFileSystem.__init__(self, baseurl)
        self.sftp = None
        self.settings = settings
        self.reinit(baseurl, create=create)

    def _delay(self):
        if self.settings:
            ms = self.settings['sftp-delay']
            if ms > 0:
                time.sleep(ms * 0.001)
        
    def _to_string(self, str_or_unicode):
        if type(str_or_unicode) is unicode:
            return str_or_unicode.encode('utf-8')
        else:
            return str_or_unicode
        
    def connect(self):
        if not self._connect_openssh():
            self._connect_paramiko()
        if self.create_path_if_missing and not self.exists(self.path):
            self.mkdir(self.path)
        self.chdir(self.path)

    def _connect_paramiko(self):
        self.transport = paramiko.Transport((self.host, self.port))
        self.transport.connect()
        self._check_host_key(self.host)
        self._authenticate(self.user)
        self.sftp = paramiko.SFTPClient.from_transport(self.transport)

    def _connect_openssh(self):
        args = ['ssh',
                '-oForwardX11=no', '-oForwardAgent=no',
                '-oClearAllForwardings=yes', '-oProtocol=2',
                '-p', str(self.port),
                '-l', self.user,
                '-s', self.host, 'sftp']

        try:
            proc = subprocess.Popen(args,
                                    stdin=subprocess.PIPE,
                                    stdout=subprocess.PIPE,
                                    close_fds=True)
        except OSError:
            return False

        self.transport = None
        self.sftp = paramiko.SFTPClient(SSHChannelAdapter(proc))
        return True

    def _check_host_key(self, hostname):
        key = self.transport.get_remote_server_key()
        known_hosts = os.path.expanduser('~/.ssh/known_hosts')
        keys = paramiko.util.load_host_keys(known_hosts)
        if hostname not in keys:
            raise obnamlib.Error('Host not in known_hosts: %s' % hostname)
        elif not keys[hostname].has_key(key.get_name()):
            raise obnamlib.Error('No host key for %s' % hostname)
        elif keys[hostname][key.get_name()] != key:
            raise obnamlib.Error('Host key has changed for %s' % hostname)
    
    def _authenticate(self, username):
        agent = paramiko.Agent()
        agent_keys = agent.get_keys()
        for key in agent_keys:
            try:
                self.transport.auth_publickey(username, key)
                return
            except paramiko.SSHException:
                pass
        raise obnamlib.Error('Can\'t authenticate to SSH server using agent.')

    def close(self):
        self.sftp.close()
        if self.transport:
            self.transport.close()
            self.transport = None
        self.sftp = None
        obnamlib.VirtualFileSystem.close(self)
        self._delay()

    @ioerror_to_oserror
    def reinit(self, baseurl, create=False):
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
        self.create_path_if_missing = create

        self._delay()
        
        if self.sftp:
            if create and not self.exists(path):
                self.mkdir(path)
                self.create_path_if_missing = False # only create first time
            self.sftp.chdir(path)

    def _get_username(self):
        return pwd.getpwuid(os.getuid()).pw_name

    def getcwd(self):
        self._delay()
        return self._to_string(self.sftp.getcwd())

    @ioerror_to_oserror
    def chdir(self, pathname):
        self._delay()
        self.sftp.chdir(pathname)

    @ioerror_to_oserror
    def listdir(self, pathname):
        self._delay()
        return [self._to_string(x) for x in self.sftp.listdir(pathname)]

    def _force_32bit_timestamp(self, timestamp):
        if timestamp is None:
            return None

        max_int32 = 2**31 - 1 # max positive 32 signed integer value
        if timestamp > max_int32:
            timestamp -= 2**32
            if timestamp > max_int32:
                timestamp = max_int32 # it's too large, need to lose info
        return timestamp

    def _fix_stat(self, pathname, st):
        # SFTP and/or paramiko fail to return some of the required fields,
        # so we add them, using faked data.
        defaults = {
            'st_blocks': (st.st_size / 512) +
                         (1 if st.st_size % 512 else 0),
            'st_dev': 0,
            'st_ino': int(hashlib.md5(pathname).hexdigest()[:8], 16),
            'st_nlink': 1,
        }
        for name, value in defaults.iteritems():
            if not hasattr(st, name):
                setattr(st, name, value)

        # Paramiko seems to deal with unsigned timestamps only, at least
        # in version 1.7.6. We therefore force the timestamps into
        # a signed 32-bit value. This limits the range, but allows
        # timestamps that are negative (before 1970). Once paramiko is
        # fixed, this code can be removed.
        st.st_mtime = self._force_32bit_timestamp(st.st_mtime)
        st.st_atime = self._force_32bit_timestamp(st.st_atime)

        return st        

    @ioerror_to_oserror
    def listdir2(self, pathname):
        self._delay()
#        return [(x, self.lstat(os.path.join(pathname, x)))
#                 for x in self.listdir(pathname)]
        return [(self._to_string(st.filename), 
                  self._fix_stat(st.filename, st)) 
                 for st in self.sftp.listdir_attr(pathname)]

    def lock(self, lockname):
        try:
            self.write_file(lockname, '')
        except IOError, e:
            if e.errno == errno.EEXIST:
                raise obnamlib.Error('Lock %s already exists' % lockname)
            else:
                raise

    def unlock(self, lockname):
        self._remove_if_exists(lockname)

    def exists(self, pathname):
        self._delay()
        try:
            self.lstat(pathname)
        except OSError:
            return False
        else:
            return True

    def isdir(self, pathname):
        self._delay()
        try:
            st = self.lstat(pathname)
        except OSError:
            return False
        else:
            return stat.S_ISDIR(st.st_mode)

    def mknod(self, pathname, mode):
        # SFTP does not provide an mknod, so we can't do this. We 
        # raise an exception, so upper layers can handle this (we _could_
        # just fail silently, but that would be silly.)
        raise NotImplementedError('mknod on SFTP: %s' % pathname)

    @ioerror_to_oserror
    def mkdir(self, pathname):
        self._delay()
        self.sftp.mkdir(pathname)
        
    @ioerror_to_oserror
    def makedirs(self, pathname):
        self._delay()
        parent = os.path.dirname(pathname)
        if parent and parent != pathname and not self.exists(parent):
            self.makedirs(parent)
        self.mkdir(pathname)

    @ioerror_to_oserror
    def rmdir(self, pathname):
        self._delay()
        self.sftp.rmdir(pathname)
        
    @ioerror_to_oserror
    def remove(self, pathname):
        self._delay()
        self.sftp.remove(pathname)

    def _remove_if_exists(self, pathname):
        '''Like remove, but OK if file does not exist.'''
        try:
            self.remove(pathname)
        except OSError, e:
            if e.errno != errno.ENOENT:
                raise

    @ioerror_to_oserror
    def rename(self, old, new):
        self._delay()
        self._remove_if_exists(new)
        self.sftp.rename(old, new)
    
    @ioerror_to_oserror
    def lstat(self, pathname):
        self._delay()
        st = self.sftp.lstat(pathname)
        self._fix_stat(pathname, st)
        return st

    @ioerror_to_oserror
    def lchown(self, pathname, uid, gid):
        self._delay()
        if stat.S_ISLNK(self.lstat(pathname).st_mode):
            logging.warning('NOT changing ownership of symlink %s' % pathname)
        else:
            self.sftp.chown(pathname, uid, gid)
        
    @ioerror_to_oserror
    def chmod(self, pathname, mode):
        self._delay()
        self.sftp.chmod(pathname, mode)
        
    @ioerror_to_oserror
    def lutimes(self, pathname, atime, mtime):
        # FIXME: This does not work for symlinks!
        # Sftp does not have a way of doing that. This means if the restore
        # target is over sftp, symlinks and their targets will have wrong
        # mtimes.
        self._delay()
        if getattr(self, 'lutimes_warned', False):
            logging.warning('lutimes used over SFTP, this does not work '
                            'against symlinks (warning appears only first '
                            'time)')
            self.lutimes_warned = True
        self.sftp.utime(pathname, (atime, mtime))

    def link(self, existing_path, new_path):
        raise obnamlib.Error('Cannot hardlink on SFTP. Sorry.')

    def readlink(self, symlink):
        self._delay()
        return self._to_string(self.sftp.readlink(symlink))

    @ioerror_to_oserror
    def symlink(self, source, destination):
        self._delay()
        self.sftp.symlink(source, destination)

    def open(self, pathname, mode, bufsize=-1):
        self._delay()
        return self.sftp.file(pathname, mode, bufsize=bufsize)

    def cat(self, pathname):
        self._delay()
        f = self.open(pathname, 'r')
        f.prefetch()
        chunks = []
        while True:
            chunk = f.read(self.chunk_size)
            if not chunk:
                break
            chunks.append(chunk)
            self.bytes_read += len(chunk)
        f.close()
        return ''.join(chunks)

    @ioerror_to_oserror
    def write_file(self, pathname, contents):
        self._delay()
        self._write_helper(pathname, 'wx', contents)

    def _tempfile(self, dirname):
        '''Generate a filename that does not exist.
        
        This is _not_ as safe as tempfile.mkstemp. Plenty of race
        conditions. But seems to be as good as SFTP will allow.
        
        '''
        
        while True:
            i = random.randint(0, 2**64-1)
            basename = 'tmp.%x' % i
            pathname = os.path.join(dirname, basename)
            if not self.exists(pathname):
                return pathname

    @ioerror_to_oserror
    def overwrite_file(self, pathname, contents, make_backup=True):
        self._delay()
        dirname = os.path.dirname(pathname)
        tempname = self._tempfile(dirname)
        self._write_helper(tempname, 'wx', contents)

        # Rename existing to have a .bak suffix. If _that_ file already
        # exists, remove that.
        bak = pathname + ".bak"
        self._remove_if_exists(bak)
        try:
            self.rename(pathname, bak)
        except OSError, e:
            if e.errno != errno.ENOENT:
                raise
        self.rename(tempname, pathname)
        if not make_backup:
            self._remove_if_exists(bak)
        
    def _write_helper(self, pathname, mode, contents):
        self._delay()
        dirname = os.path.dirname(pathname)
        if dirname and not self.exists(dirname):
            self.makedirs(dirname)
        f = self.open(pathname, mode, bufsize=self.chunk_size)
        for pos in range(0, len(contents), self.chunk_size):
            chunk = contents[pos:pos + self.chunk_size]
            f.write(chunk)
            self.bytes_written += len(chunk)
        f.close()


class SftpPlugin(obnamlib.ObnamPlugin):

    def enable(self):
        self.app.settings.integer(['sftp-delay'],
                                  'add an artificial delay (in milliseconds) '
                                    'to all SFTP transfers')
        self.app.fsf.register('sftp', SftpFS, settings=self.app.settings)

