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
import stat
import tempfile
import time
import unittest

import obnamlib


class ClientMetadataTreeTests(unittest.TestCase):

    def current_time(self):
        return time.time() if self.now is None else self.now

    def setUp(self):
        self.now = None
        self.tempdir = tempfile.mkdtemp()
        fs = obnamlib.LocalFS(self.tempdir)
        self.hooks = obnamlib.HookManager()
        self.hooks.new('repository-toplevel-init')
        self.client = obnamlib.ClientMetadataTree(fs, 'clientid',
                                   obnamlib.DEFAULT_NODE_SIZE,
                                   obnamlib.DEFAULT_UPLOAD_QUEUE_SIZE,
                                   obnamlib.DEFAULT_LRU_SIZE, self)
        self.file_size = 123
        self.file_metadata = obnamlib.Metadata(st_mode=stat.S_IFREG | 0666,
                                               st_size=self.file_size)
        self.file_encoded = obnamlib.encode_metadata(self.file_metadata)
        
    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def test_has_not_current_generation_initially(self):
        self.assertEqual(self.client.tree, None)
    
    def test_lists_no_generations_initially(self):
        self.assertEqual(self.client.list_generations(), [])

    def test_starts_generation(self):
        self.now = 12765
        self.client.start_generation()
        self.assertNotEqual(self.client.tree, None)
        
        def lookup(x):
            key = self.client.genkey(x)
            return self.client._lookup_int(self.client.tree, key)

        genid = self.client.get_generation_id(self.client.tree)
        self.assertEqual(lookup(self.client.GEN_ID), genid)
        self.assertEqual(lookup(self.client.GEN_STARTED), 12765)
        self.assertFalse(self.client.get_is_checkpoint(genid))

    def test_starts_second_generation(self):
        self.now = 1
        self.client.start_generation()
        genid1 = self.client.get_generation_id(self.client.tree)
        self.client.commit()
        self.assertEqual(self.client.tree, None)
        self.now = 2
        self.client.start_generation()
        self.assertNotEqual(self.client.tree, None)
        
        def lookup(x):
            key = self.client.genkey(x)
            return self.client._lookup_int(self.client.tree, key)

        genid2 = self.client.get_generation_id(self.client.tree)
        self.assertEqual(lookup(self.client.GEN_ID), genid2)
        self.assertNotEqual(genid1, genid2)
        self.assertEqual(lookup(self.client.GEN_STARTED), 2)
        self.assertFalse(self.client.get_is_checkpoint(genid2))
        self.assertEqual(self.client.list_generations(), [genid1, genid2])

    def test_sets_is_checkpoint(self):
        self.client.start_generation()
        genid = self.client.get_generation_id(self.client.tree)
        self.client.set_current_generation_is_checkpoint(True)
        self.assert_(self.client.get_is_checkpoint(genid))

    def test_unsets_is_checkpoint(self):
        self.client.start_generation()
        genid = self.client.get_generation_id(self.client.tree)
        self.client.set_current_generation_is_checkpoint(True)
        self.client.set_current_generation_is_checkpoint(False)
        self.assertFalse(self.client.get_is_checkpoint(genid))

    def test_removes_generation(self):
        self.client.start_generation()
        self.client.commit()
        genid = self.client.list_generations()[0]
        self.client.remove_generation(genid)
        self.assertEqual(self.client.list_generations(), [])

    def test_removes_started_generation(self):
        self.client.start_generation()
        self.client.remove_generation(self.client.list_generations()[0])
        self.assertEqual(self.client.list_generations(), [])
        self.assertEqual(self.client.tree, None)

    def test_started_generation_has_start_time(self):
        self.now = 1
        self.client.start_generation()
        genid = self.client.get_generation_id(self.client.tree)
        self.assertEqual(self.client.get_generation_times(genid), (1, None))

    def test_committed_generation_has_times(self):
        self.now = 1
        self.client.start_generation()
        genid = self.client.get_generation_id(self.client.tree)
        self.now = 2
        self.client.commit()
        self.assertEqual(self.client.get_generation_times(genid), (1, 2))

    def test_single_empty_generation_counts_zero_files(self):
        self.client.start_generation()
        genid = self.client.get_generation_id(self.client.tree)
        self.client.commit()
        self.assertEqual(self.client.get_generation_file_count(genid), 0)

    def test_counts_files_in_first_generation(self):
        self.client.start_generation()
        genid = self.client.get_generation_id(self.client.tree)
        self.client.create('/foo', self.file_encoded)
        self.client.commit()
        self.assertEqual(self.client.get_generation_file_count(genid), 1)

    def test_counts_new_files_in_second_generation(self):
        self.client.start_generation()
        self.client.create('/foo', self.file_encoded)
        self.client.commit()

        self.client.start_generation()
        genid = self.client.get_generation_id(self.client.tree)
        self.client.create('/bar', self.file_encoded)
        self.client.commit()

        self.assertEqual(self.client.get_generation_file_count(genid), 2)

    def test_discounts_deleted_files_in_second_generation(self):
        self.client.start_generation()
        self.client.create('/foo', self.file_encoded)
        self.client.commit()

        self.client.start_generation()
        genid = self.client.get_generation_id(self.client.tree)
        self.client.remove('/foo')
        self.client.commit()

        self.assertEqual(self.client.get_generation_file_count(genid), 0)

    def test_does_not_increment_count_for_recreated_files(self):
        self.client.start_generation()
        self.client.create('/foo', self.file_encoded)
        self.client.commit()

        self.client.start_generation()
        genid = self.client.get_generation_id(self.client.tree)
        self.client.create('/foo', self.file_encoded)
        self.client.commit()

        self.assertEqual(self.client.get_generation_file_count(genid), 1)

    def test_single_empty_generation_has_no_data(self):
        self.client.start_generation()
        genid = self.client.get_generation_id(self.client.tree)
        self.client.commit()
        self.assertEqual(self.client.get_generation_data(genid), 0)

    def test_has_data_in_first_generation(self):
        self.client.start_generation()
        genid = self.client.get_generation_id(self.client.tree)
        self.client.create('/foo', self.file_encoded)
        self.client.commit()
        self.assertEqual(self.client.get_generation_data(genid),
                         self.file_size)

    def test_counts_new_files_in_second_generation(self):
        self.client.start_generation()
        self.client.create('/foo', self.file_encoded)
        self.client.commit()

        self.client.start_generation()
        genid = self.client.get_generation_id(self.client.tree)
        self.client.create('/bar', self.file_encoded)
        self.client.commit()

        self.assertEqual(self.client.get_generation_data(genid),
                         2 * self.file_size)

    def test_counts_replaced_data_in_second_generation(self):
        self.client.start_generation()
        self.client.create('/foo', self.file_encoded)
        self.client.commit()

        self.client.start_generation()
        genid = self.client.get_generation_id(self.client.tree)
        self.client.create('/foo', self.file_encoded)
        self.client.commit()

        self.assertEqual(self.client.get_generation_data(genid),
                         self.file_size)

    def test_discounts_deleted_data_in_second_generation(self):
        self.client.start_generation()
        self.client.create('/foo', self.file_encoded)
        self.client.commit()

        self.client.start_generation()
        genid = self.client.get_generation_id(self.client.tree)
        self.client.remove('/foo')
        self.client.commit()

        self.assertEqual(self.client.get_generation_data(genid), 0)

    def test_does_not_increment_data_for_recreated_files(self):
        self.client.start_generation()
        self.client.create('/foo', self.file_encoded)
        self.client.commit()

        self.client.start_generation()
        genid = self.client.get_generation_id(self.client.tree)
        self.client.create('/foo', self.file_encoded)
        self.client.commit()

        self.assertEqual(self.client.get_generation_data(genid), 
                         self.file_size)

    def test_finds_generation_the_first_time(self):
        self.client.start_generation()
        tree = self.client.tree
        genid = self.client.get_generation_id(tree)
        self.client.commit()
        self.assertEqual(self.client.find_generation(genid), tree)

    def test_finds_generation_the_second_time(self):
        self.client.start_generation()
        tree = self.client.tree
        genid = self.client.get_generation_id(tree)
        self.client.commit()
        self.client.find_generation(genid)
        self.assertEqual(self.client.find_generation(genid), tree)

    def test_find_generation_raises_keyerror_for_empty_forest(self):
        self.client.init_forest()
        self.assertRaises(KeyError, self.client.find_generation, 0)

    def test_find_generation_raises_keyerror_for_unknown_generation(self):
        self.assertRaises(KeyError, self.client.find_generation, 0)


class ClientMetadataTreeFileOpsTests(unittest.TestCase):

    def current_time(self):
        return time.time() if self.now is None else self.now

    def setUp(self):
        self.now = None
        self.tempdir = tempfile.mkdtemp()
        fs = obnamlib.LocalFS(self.tempdir)
        self.hooks = obnamlib.HookManager()
        self.hooks.new('repository-toplevel-init')
        self.client = obnamlib.ClientMetadataTree(fs, 'clientid',
                                            obnamlib.DEFAULT_NODE_SIZE,
                                            obnamlib.DEFAULT_UPLOAD_QUEUE_SIZE,
                                            obnamlib.DEFAULT_LRU_SIZE, 
                                            self)
        self.client.start_generation()
        self.clientid = self.client.get_generation_id(self.client.tree)
        self.file_metadata = obnamlib.Metadata(st_mode=stat.S_IFREG | 0666)
        self.file_encoded = obnamlib.encode_metadata(self.file_metadata)
        self.dir_metadata = obnamlib.Metadata(st_mode=stat.S_IFDIR | 0777)
        self.dir_encoded = obnamlib.encode_metadata(self.dir_metadata)
        
    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def test_has_empty_root_initially(self):
        self.assertEqual(self.client.listdir(self.clientid, '/'), [])

    def test_has_no_metadata_initially(self):
        self.assertRaises(KeyError, self.client.get_metadata, self.clientid, 
                          '/foo')

    def test_sets_metadata(self):
        self.client.set_metadata('/foo', self.file_encoded)
        self.assertEqual(self.client.get_metadata(self.clientid, '/foo'), 
                         self.file_encoded)

    def test_creates_file_at_root(self):
        self.client.create('/foo', self.file_encoded)
        self.assertEqual(self.client.listdir(self.clientid, '/'), ['foo'])
        self.assertEqual(self.client.get_metadata(self.clientid, '/foo'),
                         self.file_encoded)

    def test_removes_file_at_root(self):
        self.client.create('/foo', self.file_encoded)
        self.client.remove('/foo')
        self.assertEqual(self.client.listdir(self.clientid, '/'), [])
        self.assertRaises(KeyError, self.client.get_metadata, 
                          self.clientid, '/foo')

    def test_creates_directory_at_root(self):
        self.client.create('/foo', self.dir_encoded)
        self.assertEqual(self.client.listdir(self.clientid, '/'), ['foo'])
        self.assertEqual(self.client.get_metadata(self.clientid, '/foo'), 
                         self.dir_encoded)

    def test_removes_directory_at_root(self):
        self.client.create('/foo', self.dir_encoded)
        self.client.remove('/foo')
        self.assertEqual(self.client.listdir(self.clientid, '/'), [])
        self.assertRaises(KeyError, self.client.get_metadata, 
                          self.clientid, '/foo')

    def test_creates_directory_and_files_and_subdirs(self):
        self.client.create('/foo', self.dir_encoded)
        self.client.create('/foo/foobar', self.file_encoded)
        self.client.create('/foo/bar', self.dir_encoded)
        self.client.create('/foo/bar/baz', self.file_encoded)
        self.assertEqual(self.client.listdir(self.clientid, '/'), ['foo'])
        self.assertEqual(sorted(self.client.listdir(self.clientid, '/foo')), 
                         ['bar', 'foobar'])
        self.assertEqual(self.client.listdir(self.clientid, '/foo/bar'), 
                         ['baz'])
        self.assertEqual(self.client.get_metadata(self.clientid, '/foo'), 
                         self.dir_encoded)
        self.assertEqual(self.client.get_metadata(self.clientid, '/foo/bar'), 
                         self.dir_encoded)
        self.assertEqual(self.client.get_metadata(self.clientid, '/foo/foobar'), 
                         self.file_encoded)
        self.assertEqual(self.client.get_metadata(self.clientid, 
                                                  '/foo/bar/baz'), 
                         self.file_encoded)

    def test_removes_directory_and_files_and_subdirs(self):
        self.client.create('/foo', self.dir_encoded)
        self.client.create('/foo/foobar', self.file_encoded)
        self.client.create('/foo/bar', self.dir_encoded)
        self.client.create('/foo/bar/baz', self.file_encoded)
        self.client.remove('/foo')
        self.assertEqual(self.client.listdir(self.clientid, '/'), [])
        self.assertRaises(KeyError, self.client.get_metadata, 
                          self.clientid, '/foo')
        self.assertRaises(KeyError, self.client.get_metadata, 
                          self.clientid, '/foo/foobar')
        self.assertRaises(KeyError, self.client.get_metadata, 
                          self.clientid, '/foo/bar')
        self.assertRaises(KeyError, self.client.get_metadata, 
                          self.clientid, '/foo/bar/baz')

    def test_has_no_file_chunks_initially(self):
        self.assertEqual(self.client.get_file_chunks(self.clientid, '/foo'), [])

    def test_sets_file_chunks(self):
        self.client.set_file_chunks('/foo', [1, 2, 3])
        self.assertEqual(self.client.get_file_chunks(self.clientid, '/foo'), 
                         [1, 2, 3])

    def test_appends_file_chunks_to_empty_list(self):
        self.client.append_file_chunks('/foo', [1, 2, 3])
        self.assertEqual(self.client.get_file_chunks(self.clientid, '/foo'), 
                         [1, 2, 3])

    def test_appends_file_chunks_to_nonempty_list(self):
        self.client.set_file_chunks('/foo', [1, 2, 3])
        self.client.append_file_chunks('/foo', [4, 5, 6])
        self.assertEqual(self.client.get_file_chunks(self.clientid, '/foo'), 
                         [1, 2, 3, 4, 5, 6])
                         
    def test_generation_has_no_chunk_refs_initially(self):
        minkey = self.client.chunk_key(0, 0)
        maxkey = self.client.chunk_key(obnamlib.MAX_ID, obnamlib.MAX_ID)
        self.assertEqual(list(self.client.tree.lookup_range(minkey, maxkey)), 
                         [])
                         
    def test_generation_has_no_chunk_refs_initially(self):
        minkey = self.client.chunk_key(0, 0)
        maxkey = self.client.chunk_key(obnamlib.MAX_ID, obnamlib.MAX_ID)
        self.assertEqual(list(self.client.tree.lookup_range(minkey, maxkey)), 
                         [])

    def test_sets_file_chunks(self):
        self.client.set_file_chunks('/foo', [1, 2, 3])
        self.assertEqual(self.client.get_file_chunks(self.clientid, '/foo'), 
                         [1, 2, 3])
                         
    def test_generation_has_no_chunk_refs_initially(self):
        minkey = self.client.chunk_key(0, 0)
        maxkey = self.client.chunk_key(obnamlib.MAX_ID, obnamlib.MAX_ID)
        self.assertEqual(list(self.client.tree.lookup_range(minkey, maxkey)), 
                         [])

    def test_set_file_chunks_adds_chunk_refs(self):
        self.client.set_file_chunks('/foo', [1, 2])
        file_id = self.client.get_file_id(self.client.tree, '/foo')
        minkey = self.client.chunk_key(0, 0)
        maxkey = self.client.chunk_key(obnamlib.MAX_ID, obnamlib.MAX_ID)
        self.assertEqual(set(self.client.tree.lookup_range(minkey, maxkey)), 
                         set([(self.client.chunk_key(1, file_id), ''),
                              (self.client.chunk_key(2, file_id), '')]))

    def test_set_file_chunks_removes_now_unused_chunk_refs(self):
        self.client.set_file_chunks('/foo', [1, 2])
        self.client.set_file_chunks('/foo', [1])
        file_id = self.client.get_file_id(self.client.tree, '/foo')
        minkey = self.client.chunk_key(0, 0)
        maxkey = self.client.chunk_key(obnamlib.MAX_ID, obnamlib.MAX_ID)
        self.assertEqual(list(self.client.tree.lookup_range(minkey, maxkey)), 
                         [(self.client.chunk_key(1, file_id), '')])

    def test_remove_removes_chunk_refs(self):
        self.client.set_file_chunks('/foo', [1, 2])
        self.client.remove('/foo')
        minkey = self.client.chunk_key(0, 0)
        maxkey = self.client.chunk_key(obnamlib.MAX_ID, obnamlib.MAX_ID)
        self.assertEqual(list(self.client.tree.lookup_range(minkey, maxkey)), 
                         [])
        
    def test_report_chunk_not_in_use_initially(self):
        gen_id = self.client.get_generation_id(self.client.tree)
        self.assertFalse(self.client.chunk_in_use(gen_id, 0))
        
    def test_report_chunk_in_use_after_it_is(self):
        gen_id = self.client.get_generation_id(self.client.tree)
        self.client.set_file_chunks('/foo', [0])
        self.assertTrue(self.client.chunk_in_use(gen_id, 0))

    def test_lists_no_chunks_in_generation_initially(self):
        gen_id = self.client.get_generation_id(self.client.tree)
        self.assertEqual(self.client.list_chunks_in_generation(gen_id), [])

    def test_lists_used_chunks_in_generation(self):
        gen_id = self.client.get_generation_id(self.client.tree)
        self.client.set_file_chunks('/foo', [0])
        self.client.set_file_chunks('/bar', [1])
        self.assertEqual(set(self.client.list_chunks_in_generation(gen_id)), 
                         set([0, 1]))

    def test_lists_chunks_in_generation_only_once(self):
        gen_id = self.client.get_generation_id(self.client.tree)
        self.client.set_file_chunks('/foo', [0])
        self.client.set_file_chunks('/bar', [0])
        self.assertEqual(self.client.list_chunks_in_generation(gen_id), [0])

