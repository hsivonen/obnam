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
import shutil
import tempfile
import unittest

import obnamlib


class LockManagerTests(unittest.TestCase):

    def locked(self, dirname):
        return os.path.exists(os.path.join(dirname, 'lock'))

    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        self.dirnames = []
        for x in ['a', 'b', 'c']:
            dirname = os.path.join(self.tempdir, x)
            os.mkdir(dirname)
            self.dirnames.append(dirname)
        self.fs = obnamlib.LocalFS(self.tempdir)
        self.lm = obnamlib.LockManager(self.fs)
        
    def tearDown(self):
        shutil.rmtree(self.tempdir)
        
    def test_has_nothing_locked_initially(self):
        for dirname in self.dirnames:
            self.assertFalse(self.locked(dirname))

    def test_locks_single_directory(self):
        self.lm.lock(self.dirnames[0])
        self.assertTrue(self.locked(self.dirnames[0]))

