# Copyright (C) 2010  Lars Wirzenius
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


import shutil
import tempfile
import unittest

import obnamlib


class StoreRootNodeTests(unittest.TestCase):

    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        self.fs = obnamlib.LocalFS(self.tempdir)
        self.store = obnamlib.Store(self.fs)

    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def test_lists_no_hosts(self):
        self.assertEqual(self.store.list_hosts(), [])

    def test_locks_root_node(self):
        self.store.lock_root()
        self.assert_(True)
        
    def test_locking_root_node_twice_fails(self):
        self.store.lock_root()
        self.assertRaises(obnamlib.LockFail, self.store.lock_root)
        
    def test_commit_releases_lock(self):
        self.store.lock_root()
        self.store.commit_root()
        self.store.lock_root()
        self.assert_(True)
        
    def test_unlock_releases_lock(self):
        self.store.lock_root()
        self.store.unlock_root()
        self.store.lock_root()
        self.assert_(True)
        
    def test_commit_without_lock_fails(self):
        self.assertRaises(obnamlib.LockFail, self.store.commit_root)
        
    def test_unlock_root_without_lock_fails(self):
        self.assertRaises(obnamlib.LockFail, self.store.commit_root)

