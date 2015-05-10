# Copyright 2012-2014  Lars Wirzenius
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
import shutil
import tempfile
import unittest

import obnamlib


class LockManagerTests(unittest.TestCase):

    def fake_time(self):
        self.now += 1
        return self.now

    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        self.dirnames = []
        for x in ['a', 'b', 'c']:
            dirname = os.path.join(self.tempdir, x)
            os.mkdir(dirname)
            self.dirnames.append(dirname)
        self.fs = obnamlib.LocalFS(self.tempdir)
        self.timeout = 10
        self.now = 0
        self.lm = obnamlib.LockManager(self.fs, self.timeout, '')
        self.lm._time = self.fake_time
        self.lm._sleep = lambda: None

    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def test_returns_a_lock_name(self):
        self.assertEqual(type(self.lm.get_lock_name('.')), str)

    def test_has_nothing_locked_initially(self):
        for dirname in self.dirnames:
            self.assertFalse(self.lm.is_locked(dirname))
            self.assertFalse(self.lm.got_lock(dirname))

    def test_locks_single_directory(self):
        self.lm.lock([self.dirnames[0]])
        self.assertTrue(self.lm.is_locked(self.dirnames[0]))
        self.assertTrue(self.lm.got_lock(self.dirnames[0]))

    def test_unlocks_single_directory(self):
        self.lm.lock([self.dirnames[0]])
        self.lm.unlock([self.dirnames[0]])
        self.assertFalse(self.lm.is_locked(self.dirnames[0]))
        self.assertFalse(self.lm.got_lock(self.dirnames[0]))

    def test_waits_until_timeout_for_locked_directory(self):
        self.lm.lock([self.dirnames[0]])
        self.assertRaises(obnamlib.LockFail,
                          self.lm.lock, [self.dirnames[0]])
        self.assertTrue(self.now >= self.timeout)

    def test_notices_when_preexisting_lock_goes_away(self):
        self.lm.lock([self.dirnames[0]])
        self.lm._sleep = lambda: os.remove(
            self.lm.get_lock_name(self.dirnames[0]))
        self.lm.lock([self.dirnames[0]])
        self.assertTrue(True)

    def test_locks_all_directories(self):
        self.lm.lock(self.dirnames)
        for dirname in self.dirnames:
            self.assertTrue(self.lm.is_locked(dirname))
            self.assertTrue(self.lm.got_lock(dirname))

    def test_unlocks_all_directories(self):
        self.lm.lock(self.dirnames)
        self.lm.unlock(self.dirnames)
        for dirname in self.dirnames:
            self.assertFalse(self.lm.is_locked(dirname))
            self.assertFalse(self.lm.got_lock(dirname))

    def test_does_not_lock_anything_if_one_lock_fails(self):
        self.lm.lock([self.dirnames[-1]])
        self.assertRaises(obnamlib.LockFail, self.lm.lock, self.dirnames)
        for dirname in self.dirnames[:-1]:
            self.assertFalse(self.lm.is_locked(dirname))
            self.assertFalse(self.lm.got_lock(dirname))
        self.assertTrue(self.lm.is_locked(self.dirnames[-1]))
