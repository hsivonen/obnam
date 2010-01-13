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
        
    def test_lists_no_generations_when_readonly(self):
        self.store.open_host('hostname')
        self.assertEqual(self.store.list_generations(), [])
        
    def test_lists_no_generations_when_locked(self):
        self.store.lock_host('hostname')
        self.assertEqual(self.store.list_generations(), [])
        
    def test_listing_generations_fails_if_host_is_not_open(self):
        self.assertRaises(obnamlib.Error, self.store.list_generations)

    def test_not_making_new_generation(self):
        self.assertEqual(self.store.new_generation, None)

    def test_starting_new_generation_without_lock_fails(self):
        self.assertRaises(obnamlib.LockFail, self.store.start_generation)

    def test_starting_new_generation_works(self):
        self.store.lock_host('hostname')
        self.store.start_generation()
        self.assert_(self.store.new_generation)

    def test_starting_second_new_generation_fails(self):
        self.store.lock_host('hostname')
        self.store.start_generation()
        self.assertRaises(obnamlib.Error, self.store.start_generation)

    def test_new_generation_has_root_dir_only(self):
        self.store.lock_host('hostname')
        gen = self.store.start_generation()
        self.assertEqual(self.store.listdir(gen, '/'), [])

    def test_create_fails_unless_generation_is_started(self):
        self.assertRaises(obnamlib.Error, self.store.create, None, '', None)

    def test_create_adds_file(self):
        self.store.lock_host('hostname')
        gen = self.store.start_generation()
        self.store.create(gen, '/foo', obnamlib.Metadata())
        self.assertEqual(self.store.listdir(gen, '/'), ['foo'])

    def test_remove_removes_file(self):
        self.store.lock_host('hostname')
        gen = self.store.start_generation()
        self.store.create(gen, '/foo', obnamlib.Metadata())
        self.store.remove(gen, '/foo')
        self.assertEqual(self.store.listdir(gen, '/'), [])

    def test_remove_removes_directory_tree(self):
        self.store.lock_host('hostname')
        gen = self.store.start_generation()
        self.store.create(gen, '/foo/bar', obnamlib.Metadata())
        self.store.remove(gen, '/foo')
        self.assertEqual(self.store.listdir(gen, '/'), [])

