# Copyright 2012  Lars Wirzenius
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


import os
import time

import obnamlib


class LockManager(object):

    '''Lock and unlock sets of directories at once.'''

    def __init__(self, fs, timeout, client):
        self._fs = fs
        self.timeout = timeout
        data = ["[lockfile]"]
        data = data + ["client=" + client]
        data = data + ["pid=%d" % os.getpid()]
        data = data + self._read_boot_id()
        self.data = '\r\n'.join(data)

    def _read_boot_id(self): # pragma: no cover
        try:
            with open("/proc/sys/kernel/random/boot_id", "r") as f:
                boot_id = f.read().strip()
        except:
            return []
        else:
            return ["boot_id=%s" % boot_id]

    def _time(self): # pragma: no cover
        return time.time()

    def _sleep(self): # pragma: no cover
        time.sleep(1)

    def sort(self, dirnames):
        def bytelist(s):
            return [ord(s) for s in str(s)]
        return sorted(dirnames, key=bytelist)

    def _lockname(self, dirname):
        return os.path.join(dirname, 'lock')


    def _lock_one(self, dirname):
        started = self._time()
        while True:
            lock_name = self._lockname(dirname)
            try:
                self._fs.lock(lock_name, self.data)
            except obnamlib.LockFail:
                if self._time() - started >= self.timeout:
                    raise obnamlib.LockFail('Lock timeout: %s' % lock_name)
            else:
                return
            self._sleep()

    def _unlock_one(self, dirname):
        self._fs.unlock(self._lockname(dirname))

    def is_locked(self, dirname):
        '''Is the given directory locked?

        Note the usual race conditions between testing and locking.

        '''

        return self._fs.exists(self._lockname(dirname))

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

