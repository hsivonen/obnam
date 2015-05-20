# Copyright 2012-2015  Lars Wirzenius
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


import errno
import os
import time

import obnamlib


class LockManager(object):

    '''Lock and unlock sets of directories at once.'''

    def __init__(self, fs, timeout, client):
        self._fs = fs
        self.timeout = timeout
        self._got_locks = []

    def _time(self): # pragma: no cover
        return time.time()

    def _sleep(self): # pragma: no cover
        time.sleep(1)

    def sort(self, dirnames):
        def bytelist(s):
            return [ord(s) for s in str(s)]
        return sorted(dirnames, key=bytelist)

    def get_lock_name(self, dirname):
        return os.path.join(dirname, 'lock')

    def _lock_one(self, dirname):
        started = self._time()
        while True:
            lock_name = self.get_lock_name(dirname)
            try:
                self._fs.lock(lock_name)
            except obnamlib.LockFail:
                if self._time() - started >= self.timeout:
                    raise obnamlib.LockFail(
                        lock_name=lock_name,
                        reason='timeout')
            else:
                self._got_locks.append(dirname)
                return
            self._sleep()

    def _unlock_one(self, dirname):
        self._fs.unlock(self.get_lock_name(dirname))
        if dirname in self._got_locks:
            self._got_locks.remove(dirname)

    def is_locked(self, dirname):
        '''Is the given directory locked?

        Note the usual race conditions between testing and locking.

        '''

        return self._fs.exists(self.get_lock_name(dirname))

    def got_lock(self, dirname):
        '''Does this lock manager hold the lock for a directory?'''
        return dirname in self._got_locks

    def lock(self, dirnames):
        '''Lock ALL the directories.'''
        we_locked = []
        for dirname in self.sort(dirnames):
            try:
                self._lock_one(dirname)
            except obnamlib.LockFail:
                self.unlock(we_locked)
                raise
            else:
                we_locked.append(dirname)

    def unlock(self, dirnames):
        '''Unlock ALL the directories.'''
        for dirname in self.sort(dirnames):
            self._unlock_one(dirname)

    def force(self, dirnames):
        '''Force all the directories to be unlocked.

        This works even if they weren't locked already.

        '''

        for dirname in self.sort(dirnames):
            self._force_one(dirname)

    def _force_one(self, dirname):
        lock_name = self.get_lock_name(dirname)
        if self._fs.exists(lock_name):
            self._fs.remove(lock_name)
        if dirname in self._got_locks:
            self._got_locks.remove(dirname)
