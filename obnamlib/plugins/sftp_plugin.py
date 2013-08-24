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
import traceback
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


def ioerror_to_oserror(method):
    '''Decorator to convert an IOError exception to OSError.

    Python's os.* raise OSError, mostly, but paramiko's corresponding
    methods raise IOError. This decorator fixes that.

    '''

    def helper(self, filename, *args, **kwargs):
        try:
            return method(self, filename, *args, **kwargs)
        except IOError, e:
            raise OSError(e.errno, e.strerror or str(e), filename)

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
        logging.debug('SSHChannelAdapter.close called')
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
        self._roundtrips = 0
        self._initial_dir = None
        self.reinit(baseurl, create=create)

    def _delay(self):
        self._roundtrips += 1
        if self.settings:
            ms = self.settings['sftp-delay']
            if ms > 0:
                time.sleep(ms * 0.001)

    def log_stats(self):
        obnamlib.VirtualFileSystem.log_stats(self)
        logging.info('VFS: baseurl=%s roundtrips=%s' %
                         (self.baseurl, self._roundtrips))

    def _to_string(self, str_or_unicode):
        if type(str_or_unicode) is unicode:
            return str_or_unicode.encode('utf-8')
        else:
            return str_or_unicode

    def _create_root_if_missing(self):
        try:
            self.mkdir(self.path)
        except OSError, e:
            # sftp/paramiko does not give us a useful errno so we hope
            # for the best
            pass
        self.create_path_if_missing = False # only create once

    def connect(self):
        try_openssh = not self.settings or not self.settings['pure-paramiko']
        if not try_openssh or not self._connect_openssh():
            self._connect_paramiko()
        if self.create_path_if_missing:
            self._create_root_if_missing()
        self.chdir(self.path)
        self._initial_dir = self.getcwd()
        self.chdir(self.path)

    def _connect_openssh(self):
        args = ['ssh',
                '-oForwardX11=no', '-oForwardAgent=no',
                '-oClearAllForwardings=yes', '-oProtocol=2',
                '-s']
        # default user/port from ssh (could be a per host configuration)
        if self.port:
            args += ['-p', str(self.port)]
        if self.user:
            args += ['-l', self.user]
        if self.settings and self.settings['ssh-key']:
            args += ['-i', self.settings['ssh-key']]
        if self.settings and self.settings['strict-ssh-host-keys']:
            args += ['-o', 'StrictHostKeyChecking=yes']
        if self.settings and self.settings['ssh-known-hosts']:
            args += ['-o',
                     'UserKnownHostsFile=%s' %
                        self.settings['ssh-known-hosts']]
        args += [self.host, 'sftp']

        logging.debug('executing openssh: %s' % args)
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

    def _connect_paramiko(self):
        logging.debug(
            'connect_paramiko: host=%s port=%s' % (self.host, self.port))
        if self.port:
            remote = (self.host, self.port)
        else:
            remote = (self.host)
        self.transport = paramiko.Transport(remote)
        self.transport.connect()
        logging.debug('connect_paramiko: connected')
        try:
            self._check_host_key(self.host)
        except BaseException, e:
            self.transport.close()
            self.transport = None
            raise
        logging.debug('connect_paramiko: host key checked')
        self._authenticate(self.user)
        logging.debug('connect_paramiko: authenticated')
        self.sftp = paramiko.SFTPClient.from_transport(self.transport)
        logging.debug('connect_paramiko: end')

    def _check_host_key(self, hostname):
        logging.debug('checking ssh host key for %s' % hostname)

        offered_key = self.transport.get_remote_server_key()

        known_hosts_path = self.settings['ssh-known-hosts']
        known_hosts = paramiko.util.load_host_keys(known_hosts_path)

        known_keys = known_hosts.lookup(hostname)
        if known_keys is None:
            if self.settings['strict-ssh-host-keys']:
                raise obnamlib.Error('No known host key for %s' % hostname)
            logging.warning('No known host keys for %s; accepting offered key'
                            % hostname)
            return

        offered_type = offered_key.get_name()
        if not known_keys.has_key(offered_type):
            if self.settings['strict-ssh-host-keys']:
                raise obnamlib.Error('No known type %s host key for %s' %
                                     (offered_type, hostname))
            logging.warning('No known host key of type %s for %s; accepting '
                            'offered key' % (offered_type, hostname))

        known_key = known_keys[offered_type]
        if offered_key != known_key:
            raise obnamlib.Error('SSH server %s offered wrong public key' %
                                 hostname)

        logging.debug('Host key for %s OK' % hostname)

    def _authenticate(self, username):
        if not username:
            username = self._get_username()
        for key in self._find_auth_keys():
            try:
                self.transport.auth_publickey(username, key)
                return
            except paramiko.SSHException:
                pass
        raise obnamlib.Error('Can\'t authenticate to SSH server using key.')

    def _find_auth_keys(self):
        if self.settings and self.settings['ssh-key']:
            return [self._load_from_key_file(self.settings['ssh-key'])]
        else:
            return self._load_from_agent()

    def _load_from_key_file(self, filename):
        try:
            key = paramiko.RSAKey.from_private_key_file(filename)
        except paramiko.PasswordRequiredException:
            password = getpass.getpass('RSA key password for %s: ' %
                                        filename)
            key = paramiko.RSAKey.from_private_key_file(filename, password)
        return key

    def _load_from_agent(self):
        agent = paramiko.Agent()
        return agent.get_keys()

    def close(self):
        logging.debug('SftpFS.close called')
        self.sftp.close()
        self.sftp = None
        if self.transport:
            self.transport.close()
            self.transport = None
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
            user = None

        if ':' in netloc:
            host, port = netloc.split(':', 1)
            if port == '':
                port = None
            else:
                try:
                    port = int(port)
                except ValueError, e:
                    msg = ('Invalid port number %s in %s: %s' %
                            (port, baseurl, str(e)))
                    logging.error(msg)
                    raise obnamlib.Error(msg)
        else:
            host = netloc
            port = None

        if path.startswith('/~/'):
            path = path[3:]

        self.host = host
        self.port = port
        self.user = user
        self.path = path
        self.create_path_if_missing = create

        self._delay()

        if self.sftp:
            if create:
                self._create_root_if_missing()
            logging.debug('chdir to %s' % path)
            self.sftp.chdir(self._initial_dir)
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
        st.st_mtime_sec = self._force_32bit_timestamp(st.st_mtime)
        st.st_atime_sec = self._force_32bit_timestamp(st.st_atime)

        # Within Obnam, we pretend stat results have st_Xtime_sec and
        # st_Xtime_nsec, but not st_Xtime. Remove those fields.
        del st.st_mtime
        del st.st_atime

        # We only get integer timestamps, so set these explicitly to 0.
        st.st_mtime_nsec = 0
        st.st_atime_nsec = 0

        return st

    @ioerror_to_oserror
    def listdir2(self, pathname):
        self._delay()
        attrs = self.sftp.listdir_attr(pathname)
        pairs = [(self._to_string(st.filename), st) for st in attrs]
        fixed = [(name, self._fix_stat(name, st)) for name, st in pairs]
        return fixed

    def lock(self, lockname, data):
        try:
            self.write_file(lockname, data)
        except OSError, e:
            raise obnamlib.LockFail('Failure get lock %s' % lockname)

    def unlock(self, lockname):
        self._remove_if_exists(lockname)

    def exists(self, pathname):
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
    def lchmod(self, pathname, mode):
        self._delay()
        self.sftp.chmod(pathname, mode)

    @ioerror_to_oserror
    def lutimes(self, pathname, atime_sec, atime_nsec, mtime_sec, mtime_nsec):
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
        self.sftp.utime(pathname, (atime_sec, mtime_sec))

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
        try:
            f = self.open(pathname, 'wx')
        except (IOError, OSError), e:
            # When the path to the file to be written does not
            # exist, we try to create the directories below. Note that
            # some SFTP servers return EACCES instead of ENOENT
            # when the path to the file does not exist, so we
            # do not raise an exception here for both ENOENT
            # and EACCES.
            if e.errno != errno.ENOENT and e.errno != errno.EACCES:
                raise
            dirname = os.path.dirname(pathname)
            self.makedirs(dirname)
            f = self.open(pathname, 'wx')

        self._write_helper(f, contents)
        f.close()

    def _tempfile(self, dirname):
        '''Create a new file with a random name, return file handle and name.'''

        if dirname:
            try:
                self.makedirs(dirname)
            except OSError:
                # We ignore the error, on the assumption that it was due
                # to the directory already existing. If it didn't exist
                # and the error was for something else, then we'll catch
                # that when we open the file for writing.
                pass

        while True:
            i = random.randint(0, 2**64-1)
            basename = 'tmp.%x' % i
            pathname = os.path.join(dirname, basename)
            try:
                f = self.open(pathname, 'wx', bufsize=self.chunk_size)
            except OSError:
                pass
            else:
                return f, pathname

    @ioerror_to_oserror
    def overwrite_file(self, pathname, contents):
        self._delay()
        dirname = os.path.dirname(pathname)
        f, tempname = self._tempfile(dirname)
        self._write_helper(f, contents)
        f.close()
        self.rename(tempname, pathname)

    def _write_helper(self, f, contents):
        for pos in range(0, len(contents), self.chunk_size):
            chunk = contents[pos:pos + self.chunk_size]
            f.write(chunk)
            self.bytes_written += len(chunk)


class SftpPlugin(obnamlib.ObnamPlugin):

    def enable(self):
        ssh_group = obnamlib.option_group['ssh'] = 'SSH/SFTP'
        devel_group = obnamlib.option_group['devel']

        self.app.settings.integer(['sftp-delay'],
                                  'add an artificial delay (in milliseconds) '
                                    'to all SFTP transfers',
                                  group=devel_group)

        self.app.settings.string(['ssh-key'],
                                 'use FILENAME as the ssh RSA private key for '
                                    'sftp access (default is using keys known '
                                    'to ssh-agent)',
                                 metavar='FILENAME',
                                 group=ssh_group)

        self.app.settings.boolean(['strict-ssh-host-keys'],
                                  'require that the ssh host key must be '
                                    'known and correct to be accepted; '
                                    'default is to accept unknown keys',
                                  group=ssh_group)

        self.app.settings.string(['ssh-known-hosts'],
                                 'filename of the user\'s known hosts file '
                                    '(default: %default)',
                                 metavar='FILENAME',
                                 default=
                                    os.path.expanduser('~/.ssh/known_hosts'),
                                 group=ssh_group)

        self.app.settings.boolean(['pure-paramiko'],
                                 'do not use openssh even if available, '
                                    'use paramiko only instead',
                                  group=ssh_group)

        self.app.fsf.register('sftp', SftpFS, settings=self.app.settings)

