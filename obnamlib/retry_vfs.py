# Copyright (C) 2008-2015  Lars Wirzenius <liw@liw.fi>
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

import logging
import time

import obnamlib

def retry_on_failure(method):
    '''Decorator to implement creating and connecting a new delegate with
    exponential backoff.

    Takes only the name from the method being decorated. Hence, the methods
    that are supposed to be decorated should raise an exception to make it
    obvious when the decoration is missing.
    '''

    method_name = method.__name__
    def retry_on_failure_wrapper(self, *args, **kwargs):
        attempt = 0
        while True:
            try:
                return getattr(self._delegate, method_name)(*args, **kwargs)
            except OSError, e:
                while True:
                    attempt += 1
                    if attempt > self._times_to_attempt:
                        raise e
                    logging.debug(
                        'RetryVFS: baseurl=%s method=%s attempt=%d exception=%s',
                        self.baseurl, method_name, attempt, e)
                    try:
                        self._delegate.close()
                    except:
                        pass
                    delay = ((pow(self._delay_base, attempt) - self._delay_base)
                            * self._delay_factor)
                    if delay:
                        logging.debug(
                           'RetryVFS: will sleep for %d seconds',
                           delay)
                        time.sleep(delay)
                    self._init_delegate()
                    try:
                        self._delegate.connect()
                        # TODO: Need to unlock the repo here.
                        break
                    except OSError, ex:
                        logging.debug(
                           'RetryVFS: baseurl=%s reconnect attempt=%d exception=%s',
                           self.baseurl, attempt, ex)

    return retry_on_failure_wrapper

class RetryVirtualFileSystem(obnamlib.VirtualFileSystem):

    '''A virtual filesystem that wraps a different virtual file system as a
    as delegate and retries calling the delegate methods if they fail with
    exponential backoff.

    '''

    def __init__(self, baseurl, delegate_class=None, **kwargs):
        obnamlib.VirtualFileSystem.__init__(self, baseurl)
        self._delegate_class = delegate_class
        self._delegate_kwargs = kwargs

        # Maybe make the following configurable.
        # These values add up to giving up in under 23 hours.
        self._times_to_attempt = 12
        self._delay_base = 2
        self._delay_factor = 10 # seconds

        self._init_delegate()

    def _init_delegate(self):
        self._delegate = self._delegate_class(self.baseurl,
                                              **self._delegate_kwargs)

    @retry_on_failure
    def connect(self):
        raise NotImplementedError()

    @retry_on_failure
    def close(self):
        raise NotImplementedError()

    @retry_on_failure
    def reinit(self, new_baseurl, create=False):
        raise NotImplementedError()

    @retry_on_failure
    def getcwd(self):
        raise NotImplementedError()

    @retry_on_failure
    def chdir(self, pathname):
        raise NotImplementedError()

    @retry_on_failure
    def listdir(self, pathname):
        raise NotImplementedError()

    @retry_on_failure
    def listdir2(self, pathname):
        raise NotImplementedError()

    @retry_on_failure
    def lock(self, lockname):
        raise NotImplementedError()

    @retry_on_failure
    def unlock(self, lockname):
        raise NotImplementedError()

    @retry_on_failure
    def exists(self, pathname):
        raise NotImplementedError()

    @retry_on_failure
    def mknod(self, pathname, mode):
        raise NotImplementedError()

    @retry_on_failure
    def isdir(self, pathname):
        raise NotImplementedError()

    @retry_on_failure
    def mkdir(self, pathname, mode=obnamlib.NEW_DIR_MODE):
        raise NotImplementedError()

    @retry_on_failure
    def makedirs(self, pathname):
        raise NotImplementedError()

    @retry_on_failure
    def rmdir(self, pathname):
        raise NotImplementedError()

    @retry_on_failure
    def remove(self, pathname):
        raise NotImplementedError()

    @retry_on_failure
    def rename(self, old, new):
        raise NotImplementedError()

    @retry_on_failure
    def lstat(self, pathname):
        raise NotImplementedError()

    @retry_on_failure
    def get_username(self, uid):
        raise NotImplementedError()

    @retry_on_failure
    def get_groupname(self, gid):
        raise NotImplementedError()

    @retry_on_failure
    def llistxattr(self, pathname):
        raise NotImplementedError()

    @retry_on_failure
    def lgetxattr(self, pathname, attrname):
        raise NotImplementedError()

    @retry_on_failure
    def lsetxattr(self, pathname, attrname, attrvalue):
        raise NotImplementedError()

    @retry_on_failure
    def lchown(self, pathname, uid, gid):
        raise NotImplementedError()

    @retry_on_failure
    def chmod_symlink(self, pathname, mode):
        raise NotImplementedError()

    @retry_on_failure
    def chmod_not_symlink(self, pathname, mode):
        raise NotImplementedError()

    @retry_on_failure
    def lutimes(self, pathname, atime_sec, atime_nsec, mtime_sec, mtime_nsec):
        raise NotImplementedError()

    @retry_on_failure
    def link(self, existing_path, new_path):
        raise NotImplementedError()

    @retry_on_failure
    def readlink(self, symlink):
        raise NotImplementedError()

    @retry_on_failure
    def symlink(self, source, destination):
        raise NotImplementedError()

    @retry_on_failure
    def open(self, pathname, mode, bufsize=None):
        raise NotImplementedError()

    @retry_on_failure
    def cat(self, pathname):
        raise NotImplementedError()

    @retry_on_failure
    def write_file(self, pathname, contents):
        raise NotImplementedError()

    @retry_on_failure
    def overwrite_file(self, pathname, contents):
        raise NotImplementedError()
