# Copyright 2010  Lars Wirzenius
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


class ClientListTests(unittest.TestCase):

    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        fs = obnamlib.LocalFS(self.tempdir)
        self.hooks = obnamlib.HookManager()
        self.hooks.new('repository-toplevel-init')
        self.list = obnamlib.ClientList(fs, 
                                        obnamlib.DEFAULT_NODE_SIZE,
                                        obnamlib.DEFAULT_UPLOAD_QUEUE_SIZE,
                                        obnamlib.DEFAULT_LRU_SIZE, self)

    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def test_key_bytes_is_correct_length(self):
        self.assertEqual(self.list.key_bytes, 
                         len(self.list.key('foo', 12765, 0)))

    def test_unkey_unpacks_key_correctly(self):
        key = self.list.key('client name', 12765, 42)
        client_hash, client_id, subkey = self.list.unkey(key)
        self.assertEqual(client_id, 12765)
        self.assertEqual(subkey, 42)

    def test_reports_none_as_id_for_nonexistent_client(self):
        self.assertEqual(self.list.get_client_id('foo'), None)
        
    def test_lists_no_clients_when_tree_does_not_exist(self):
        self.assertEqual(self.list.list_clients(), [])

    def test_added_client_has_integer_id(self):
        self.list.add_client('foo')
        self.assert_(type(self.list.get_client_id('foo')) in [int, long])

    def test_added_client_is_listed(self):
        self.list.add_client('foo')
        self.list.set_client_keyid('foo', 'cafebeef')
        self.assertEqual(self.list.list_clients(), ['foo'])

    def test_removed_client_has_none_id(self):
        self.list.add_client('foo')
        self.list.remove_client('foo')
        self.assertEqual(self.list.get_client_id('foo'), None)
        
    def test_removed_client_has_no_keys(self):
        self.list.add_client('foo')
        client_id = self.list.get_client_id('foo')
        self.list.remove_client('foo')
        minkey = self.list.key('foo', client_id, 0)
        maxkey = self.list.key('foo', client_id, self.list.SUBKEY_MAX)
        pairs = list(self.list.tree.lookup_range(minkey, maxkey))
        self.assertEqual(pairs, [])

    def test_twice_added_client_exists_only_once(self):
        self.list.add_client('foo')
        self.list.add_client('foo')
        self.assertEqual(self.list.list_clients(), ['foo'])

    def test_adding_handles_hash_collision(self):
        def bad_hash(string):
            return '0' * 16
        self.list.hashfunc = bad_hash
        self.list.add_client('foo')
        self.list.add_client('bar')
        self.assertEqual(sorted(self.list.list_clients()), ['bar', 'foo'])
        self.assertNotEqual(self.list.get_client_id('bar'),
                            self.list.get_client_id('foo'))

    def test_client_has_no_public_key_initially(self):
        self.list.add_client('foo')
        self.assertEqual(self.list.get_client_keyid('foo'), None)

    def test_sets_client_keyid(self):
        self.list.add_client('foo')
        self.list.set_client_keyid('foo', 'cafebeef')
        self.assertEqual(self.list.get_client_keyid('foo'), 'cafebeef')

    def test_remove_client_keyid(self):
        self.list.add_client('foo')
        self.list.set_client_keyid('foo', 'cafebeef')
        self.list.set_client_keyid('foo', None)
        self.assertEqual(self.list.get_client_keyid('foo'), None)

