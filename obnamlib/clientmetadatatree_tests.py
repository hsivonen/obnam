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
import unittest

import obnamlib


class ClientMetadataTreeTests(unittest.TestCase):

    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        fs = obnamlib.LocalFS(self.tempdir)
        self.client = obnamlib.ClientMetadataTree(fs, 'clientid',
                                   obnamlib.DEFAULT_NODE_SIZE,
                                   obnamlib.DEFAULT_UPLOAD_QUEUE_SIZE,
                                   obnamlib.DEFAULT_LRU_SIZE)
        
    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def test_has_not_current_generation_initially(self):
        self.assertEqual(self.client.curgen, None)
    
    def test_lists_no_generations_initially(self):
        self.assertEqual(self.client.list_generations(), [])

    def test_starts_generation(self):
        self.client.require_forest()
        self.client.start_generation(current_time=lambda: 12765)
        self.assertNotEqual(self.client.curgen, None)
        
        def lookup(x):
            key = self.client.genkey(x)
            return self.client._lookup_int(self.client.curgen, key)

        genid = self.client.get_generation_id(self.client.curgen)
        self.assertEqual(lookup(self.client.GEN_ID), genid)
        self.assertEqual(lookup(self.client.GEN_STARTED), 12765)
        self.assertFalse(self.client.get_is_checkpoint(genid))

    def test_starts_second_generation(self):
        self.client.require_forest()
        self.client.start_generation(current_time=lambda: 1)
        genid1 = self.client.get_generation_id(self.client.curgen)
        self.client.commit()
        self.client.start_generation(current_time=lambda: 2)
        self.assertNotEqual(self.client.curgen, None)
        
        def lookup(x):
            key = self.client.genkey(x)
            return self.client._lookup_int(self.client.curgen, key)

        genid2 = self.client.get_generation_id(self.client.curgen)
        self.assertEqual(lookup(self.client.GEN_ID), genid2)
        self.assertNotEqual(genid1, genid2)
        self.assertEqual(lookup(self.client.GEN_STARTED), 2)
        self.assertFalse(self.client.get_is_checkpoint(genid2))
        self.assertEqual(self.client.list_generations(), [genid1, genid2])

    def test_sets_is_checkpoint(self):
        self.client.require_forest()
        self.client.start_generation()
        genid = self.client.get_generation_id(self.client.curgen)
        self.client.set_current_generation_is_checkpoint(True)
        self.assert_(self.client.get_is_checkpoint(genid))

    def test_unsets_is_checkpoint(self):
        self.client.require_forest()
        self.client.start_generation()
        genid = self.client.get_generation_id(self.client.curgen)
        self.client.set_current_generation_is_checkpoint(True)
        self.client.set_current_generation_is_checkpoint(False)
        self.assertFalse(self.client.get_is_checkpoint(genid))

    def test_removes_generation(self):
        self.client.require_forest()
        self.client.start_generation()
        self.client.commit()
        self.client.remove_generation(self.client.list_generations()[0])
        self.assertEqual(self.client.list_generations(), [])

    def test_removes_started_generation(self):
        self.client.require_forest()
        self.client.start_generation()
        self.client.remove_generation(self.client.list_generations()[0])
        self.assertEqual(self.client.list_generations(), [])
        self.assertEqual(self.client.curgen, None)

    def test_started_generation_has_start_time(self):
        self.client.require_forest()
        self.client.start_generation(current_time=lambda: 1)
        genid = self.client.get_generation_id(self.client.curgen)
        self.assertEqual(self.client.get_generation_times(genid), (1, None))

    def test_committed_generation_has_times(self):
        self.client.require_forest()
        self.client.start_generation(current_time=lambda: 1)
        genid = self.client.get_generation_id(self.client.curgen)
        self.client.commit(current_time=lambda: 2)
        self.assertEqual(self.client.get_generation_times(genid), (1, 2))

    def test_finds_generation_the_first_time(self):
        self.client.require_forest()
        self.client.start_generation()
        tree = self.client.curgen
        genid = self.client.get_generation_id(tree)
        self.client.commit()
        self.assertEqual(self.client.find_generation(genid), tree)

    def test_finds_generation_the_second_time(self):
        self.client.require_forest()
        self.client.start_generation()
        tree = self.client.curgen
        genid = self.client.get_generation_id(tree)
        self.client.commit()
        self.client.find_generation(genid)
        self.assertEqual(self.client.find_generation(genid), tree)

    def test_find_generation_raises_keyerror_for_empty_forest(self):
        self.client.init_forest()
        self.assertRaises(KeyError, self.client.find_generation, 0)

    def test_find_generation_raises_keyerror_for_unknown_generation(self):
        self.client.require_forest()
        self.assertRaises(KeyError, self.client.find_generation, 0)


class ClientMetadataTreeFileOpsTests(unittest.TestCase):

    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        fs = obnamlib.LocalFS(self.tempdir)
        self.client = obnamlib.ClientMetadataTree(fs, 'clientid',
                                            obnamlib.DEFAULT_NODE_SIZE,
                                            obnamlib.DEFAULT_UPLOAD_QUEUE_SIZE,
                                            obnamlib.DEFAULT_LRU_SIZE)
        self.client.require_forest()
        self.client.start_generation()
        self.clientid = self.client.get_generation_id(self.client.curgen)
        self.file_metadata = obnamlib.Metadata(st_mode=stat.S_IFREG | 0666)
        self.file_encoded = obnamlib.store.encode_metadata(self.file_metadata)
        
    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def test_has_empty_root_initially(self):
        self.assertEqual(self.client.listdir(self.clientid, '/'), [])

    def test_has_no_metadata_initially(self):
        self.assertRaises(KeyError, self.client.get_metadata, self.clientid, '/foo')

    def test_sets_metadata(self):
        self.client.set_metadata('/foo', self.file_encoded)
        self.assertEqual(self.client.get_metadata(self.clientid, '/foo'), 
                         self.file_encoded)

    def test_creates_file_at_root(self):
        self.client.create('/foo', self.file_encoded)
        self.assertEqual(self.client.listdir(self.clientid, '/'), ['foo'])

    def test_removes_file_at_root(self):
        self.client.create('/foo', self.file_encoded)
        self.client.remove('/foo')
        self.assertEqual(self.client.listdir(self.clientid, '/'), [])

    def test_has_no_file_chunks_initially(self):
        self.assertEqual(self.client.get_file_chunks(self.clientid, '/foo'), [])

    def test_sets_file_chunks(self):
        self.client.set_file_chunks('/foo', [1, 2, 3])
        self.assertEqual(self.client.get_file_chunks(self.clientid, '/foo'), 
                         [1, 2, 3])
                         
    def test_has_no_file_chunk_groups_initially(self):
        self.assertEqual(self.client.get_file_chunk_groups(self.clientid, '/foo'), 
                         [])

    def test_sets_file_chunk_groups(self):
        self.client.set_file_chunk_groups('/foo', [1, 2, 3])
        self.assertEqual(self.client.get_file_chunk_groups(self.clientid, '/foo'), 
                         [1, 2, 3])

    def test_generation_has_no_chunk_refs_initially(self):
        minkey = self.client.chunk_key(0, 0)
        maxkey = self.client.chunk_key(self.client.max_id, self.client.max_id)
        self.assertEqual(self.client.curgen.lookup_range(minkey, maxkey), [])

    def test_set_file_chunks_adds_chunk_refs(self):
        self.client.set_file_chunks('/foo', [1, 2])
        file_id = self.client.get_file_id(self.client.curgen, '/foo')
        minkey = self.client.chunk_key(0, 0)
        maxkey = self.client.chunk_key(self.client.max_id, self.client.max_id)
        self.assertEqual(set(self.client.curgen.lookup_range(minkey, maxkey)), 
                         set([(self.client.chunk_key(1, file_id), ''),
                              (self.client.chunk_key(2, file_id), '')]))

    def test_set_file_chunks_removes_now_unused_chunk_refs(self):
        self.client.set_file_chunks('/foo', [1, 2])
        self.client.set_file_chunks('/foo', [1])
        file_id = self.client.get_file_id(self.client.curgen, '/foo')
        minkey = self.client.chunk_key(0, 0)
        maxkey = self.client.chunk_key(self.client.max_id, self.client.max_id)
        self.assertEqual(self.client.curgen.lookup_range(minkey, maxkey), 
                         [(self.client.chunk_key(1, file_id), '')])

    def test_generation_has_no_chunk_group_refs_initially(self):
        minkey = self.client.cgkey(0, 0)
        maxkey = self.client.cgkey(self.client.max_id, self.client.max_id)
        self.assertEqual(self.client.curgen.lookup_range(minkey, maxkey), [])

    def test_set_file_chunks_adds_chunk_group_refs(self):
        self.client.set_file_chunk_groups('/foo', [1, 2])
        file_id = self.client.get_file_id(self.client.curgen, '/foo')
        minkey = self.client.cgkey(0, 0)
        maxkey = self.client.cgkey(self.client.max_id, self.client.max_id)
        self.assertEqual(set(self.client.curgen.lookup_range(minkey, maxkey)), 
                         set([(self.client.cgkey(1, file_id), ''),
                              (self.client.cgkey(2, file_id), '')]))

    def test_set_file_chunks_removes_now_unused_chunk_group_refs(self):
        self.client.set_file_chunk_groups('/foo', [1, 2])
        self.client.set_file_chunk_groups('/foo', [1])
        file_id = self.client.get_file_id(self.client.curgen, '/foo')
        minkey = self.client.cgkey(0, 0)
        maxkey = self.client.cgkey(self.client.max_id, self.client.max_id)
        self.assertEqual(self.client.curgen.lookup_range(minkey, maxkey), 
                         [(self.client.cgkey(1, file_id), '')])

    def test_remove_removes_chunk_refs(self):
        self.client.set_file_chunks('/foo', [1, 2])
        self.client.remove('/foo')
        minkey = self.client.cgkey(0, 0)
        maxkey = self.client.cgkey(self.client.max_id, self.client.max_id)
        self.assertEqual(self.client.curgen.lookup_range(minkey, maxkey), [])

