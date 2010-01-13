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
        
        self.otherfs = obnamlib.LocalFS(self.tempdir)
        self.other = obnamlib.Store(self.fs)

    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def test_lists_no_hosts(self):
        self.assertEqual(self.store.list_hosts(), [])

    def test_has_not_got_root_node_lock(self):
        self.assertFalse(self.store.got_root_lock)

    def test_locks_root_node(self):
        self.store.lock_root()
        self.assert_(self.store.got_root_lock)
        
    def test_locking_root_node_twice_fails(self):
        self.store.lock_root()
        self.assertRaises(obnamlib.LockFail, self.store.lock_root)
        
    def test_commit_releases_lock(self):
        self.store.lock_root()
        self.store.commit_root()
        self.assertFalse(self.store.got_root_lock)
        
    def test_unlock_releases_lock(self):
        self.store.lock_root()
        self.store.unlock_root()
        self.assertFalse(self.store.got_root_lock)
        
    def test_commit_without_lock_fails(self):
        self.assertRaises(obnamlib.LockFail, self.store.commit_root)
        
    def test_unlock_root_without_lock_fails(self):
        self.assertRaises(obnamlib.LockFail, self.store.unlock_root)

    def test_commit_when_locked_by_other_fails(self):
        self.other.lock_root()
        self.assertRaises(obnamlib.LockFail, self.store.commit_root)

    def test_unlock_root_when_locked_by_other_fails(self):
        self.other.lock_root()
        self.assertRaises(obnamlib.LockFail, self.store.unlock_root)
        
    def test_adding_host_without_root_lock_fails(self):
        self.assertRaises(obnamlib.LockFail, self.store.add_host, 'foo')
        
    def test_adds_host(self):
        self.store.lock_root()
        self.store.add_host('foo')
        self.assertEqual(self.store.list_hosts(), ['foo'])
        
    def test_adding_existing_host_fails(self):
        self.store.lock_root()
        self.store.add_host('foo')
        self.assertRaises(obnamlib.Error, self.store.add_host, 'foo')
        
    def test_removing_host_without_root_lock_fails(self):
        self.assertRaises(obnamlib.LockFail, self.store.remove_host, 'foo')
        
    def test_removing_nonexistent_host_fails(self):
        self.store.lock_root()
        self.assertRaises(obnamlib.Error, self.store.remove_host, 'foo')
        
    def test_removing_host_works(self):
        self.store.lock_root()
        self.store.add_host('foo')
        self.store.remove_host('foo')
        self.assertEqual(self.store.list_hosts(), [])


class StoreHostTests(unittest.TestCase):


    def setUp(self):
        self.tempdir = tempfile.mkdtemp()

        self.fs = obnamlib.LocalFS(self.tempdir)
        self.store = obnamlib.Store(self.fs)
        self.store.lock_root()
        self.store.add_host('hostname')
        self.store.commit_root()
        
        self.otherfs = obnamlib.LocalFS(self.tempdir)
        self.other = obnamlib.Store(self.otherfs)

    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def test_has_not_got_host_lock(self):
        self.assertFalse(self.store.got_host_lock)

    def test_locks_host(self):
        self.store.lock_host('hostname')
        self.assert_(self.store.got_host_lock)

    def test_locking_host_twice_fails(self):
        self.store.lock_host('hostname')
        self.assertRaises(obnamlib.LockFail, self.store.lock_host, 
                          'hostname')

    def test_unlock_host_releases_lock(self):
        self.store.lock_host('hostname')
        self.store.unlock_host()
        self.assertFalse(self.store.got_host_lock)

    def test_commit_host_releases_lock(self):
        self.store.lock_host('hostname')
        self.store.commit_host()
        self.assertFalse(self.store.got_host_lock)

    def test_commit_host_without_lock_fails(self):
        self.assertRaises(obnamlib.LockFail, self.store.commit_host)
        
    def test_unlock_host_without_lock_fails(self):
        self.assertRaises(obnamlib.LockFail, self.store.unlock_host)

    def test_commit_host_when_locked_by_other_fails(self):
        self.other.lock_host('hostname')
        self.assertRaises(obnamlib.LockFail, self.store.commit_host)

    def test_unlock_host_when_locked_by_other_fails(self):
        self.other.lock_host('hostname')
        self.assertRaises(obnamlib.LockFail, self.store.unlock_host)

    def test_opens_host_even_when_locked_by_other(self):
        self.other.lock_host('hostname')
        self.store.open_host('hostname')
        self.assert_(True)
