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


class GenerationStoreTests(unittest.TestCase):

    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        fs = obnamlib.LocalFS(self.tempdir)
        self.gen = obnamlib.GenerationStore(fs, 'clientid',
                                            obnamlib.DEFAULT_NODE_SIZE,
                                            obnamlib.DEFAULT_UPLOAD_QUEUE_SIZE,
                                            obnamlib.DEFAULT_LRU_SIZE)
        
    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def test_has_not_current_generation_initially(self):
        self.assertEqual(self.gen.curgen, None)
    
    def test_lists_no_generations_initially(self):
        self.assertEqual(self.gen.list_generations(), [])

    def test_starts_generation(self):
        self.gen.require_forest()
        self.gen.start_generation(current_time=lambda: 12765)
        self.assertNotEqual(self.gen.curgen, None)
        
        def lookup(x):
            key = self.gen.genkey(x)
            return self.gen._lookup_int(self.gen.curgen, key)

        genid = self.gen.get_generation_id(self.gen.curgen)
        self.assertEqual(lookup(self.gen.GEN_META_ID), genid)
        self.assertEqual(lookup(self.gen.GEN_META_STARTED), 12765)
        self.assertFalse(self.gen.get_is_checkpoint(genid))

    def test_starts_second_generation(self):
        self.gen.require_forest()
        self.gen.start_generation(current_time=lambda: 1)
        genid1 = self.gen.get_generation_id(self.gen.curgen)
        self.gen.commit()
        self.gen.start_generation(current_time=lambda: 2)
        self.assertNotEqual(self.gen.curgen, None)
        
        def lookup(x):
            key = self.gen.genkey(x)
            return self.gen._lookup_int(self.gen.curgen, key)

        genid2 = self.gen.get_generation_id(self.gen.curgen)
        self.assertEqual(lookup(self.gen.GEN_META_ID), genid2)
        self.assertNotEqual(genid1, genid2)
        self.assertEqual(lookup(self.gen.GEN_META_STARTED), 2)
        self.assertFalse(self.gen.get_is_checkpoint(genid2))
        self.assertEqual(self.gen.list_generations(), [genid1, genid2])

    def test_sets_is_checkpoint(self):
        self.gen.require_forest()
        self.gen.start_generation()
        genid = self.gen.get_generation_id(self.gen.curgen)
        self.gen.set_current_generation_is_checkpoint(True)
        self.assert_(self.gen.get_is_checkpoint(genid))

    def test_unsets_is_checkpoint(self):
        self.gen.require_forest()
        self.gen.start_generation()
        genid = self.gen.get_generation_id(self.gen.curgen)
        self.gen.set_current_generation_is_checkpoint(True)
        self.gen.set_current_generation_is_checkpoint(False)
        self.assertFalse(self.gen.get_is_checkpoint(genid))

    def test_removes_generation(self):
        self.gen.require_forest()
        self.gen.start_generation()
        self.gen.commit()
        self.gen.remove_generation(self.gen.list_generations()[0])
        self.assertEqual(self.gen.list_generations(), [])

    def test_removes_started_generation(self):
        self.gen.require_forest()
        self.gen.start_generation()
        self.gen.remove_generation(self.gen.list_generations()[0])
        self.assertEqual(self.gen.list_generations(), [])
        self.assertEqual(self.gen.curgen, None)

    def test_started_generation_has_start_time(self):
        self.gen.require_forest()
        self.gen.start_generation(current_time=lambda: 1)
        genid = self.gen.get_generation_id(self.gen.curgen)
        self.assertEqual(self.gen.get_generation_times(genid), (1, None))

    def test_committed_generation_has_times(self):
        self.gen.require_forest()
        self.gen.start_generation(current_time=lambda: 1)
        genid = self.gen.get_generation_id(self.gen.curgen)
        self.gen.commit(current_time=lambda: 2)
        self.assertEqual(self.gen.get_generation_times(genid), (1, 2))

    def test_finds_generation_the_first_time(self):
        self.gen.require_forest()
        self.gen.start_generation()
        tree = self.gen.curgen
        genid = self.gen.get_generation_id(tree)
        self.gen.commit()
        self.assertEqual(self.gen.find_generation(genid), tree)

    def test_finds_generation_the_second_time(self):
        self.gen.require_forest()
        self.gen.start_generation()
        tree = self.gen.curgen
        genid = self.gen.get_generation_id(tree)
        self.gen.commit()
        self.gen.find_generation(genid)
        self.assertEqual(self.gen.find_generation(genid), tree)

    def test_find_generation_raises_keyerror_for_empty_forest(self):
        self.gen.init_forest()
        self.assertRaises(KeyError, self.gen.find_generation, 0)

    def test_find_generation_raises_keyerror_for_unknown_generation(self):
        self.gen.require_forest()
        self.assertRaises(KeyError, self.gen.find_generation, 0)


class GenerationTreeFileOpsTests(unittest.TestCase):

    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        fs = obnamlib.LocalFS(self.tempdir)
        self.gen = obnamlib.GenerationStore(fs, 'clientid',
                                            obnamlib.DEFAULT_NODE_SIZE,
                                            obnamlib.DEFAULT_UPLOAD_QUEUE_SIZE,
                                            obnamlib.DEFAULT_LRU_SIZE)
        self.gen.require_forest()
        self.gen.start_generation()
        self.genid = self.gen.get_generation_id(self.gen.curgen)
        self.file_metadata = obnamlib.Metadata(st_mode=stat.S_IFREG | 0666)
        self.file_encoded = obnamlib.store.encode_metadata(self.file_metadata)
        
    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def test_has_empty_root_initially(self):
        self.assertEqual(self.gen.listdir(self.genid, '/'), [])

    def test_has_no_metadata_initially(self):
        self.assertRaises(KeyError, self.gen.get_metadata, self.genid, '/foo')

    def test_sets_metadata(self):
        self.gen.set_metadata('/foo', self.file_encoded)
        self.assertEqual(self.gen.get_metadata(self.genid, '/foo'), 
                         self.file_encoded)

    def test_creates_file_at_root(self):
        self.gen.create('/foo', self.file_encoded)
        self.assertEqual(self.gen.listdir(self.genid, '/'), ['foo'])

    def test_removes_file_at_root(self):
        self.gen.create('/foo', self.file_encoded)
        self.gen.remove('/foo')
        self.assertEqual(self.gen.listdir(self.genid, '/'), [])

    def test_has_no_file_chunks_initially(self):
        self.assertEqual(self.gen.get_file_chunks(self.genid, '/foo'), [])

    def test_sets_file_chunks(self):
        self.gen.set_file_chunks('/foo', [1, 2, 3])
        self.assertEqual(self.gen.get_file_chunks(self.genid, '/foo'), 
                         [1, 2, 3])

    def test_has_no_file_chunk_groups_initially(self):
        self.assertEqual(self.gen.get_file_chunk_groups(self.genid, '/foo'), 
                         [])

    def test_sets_file_chunk_groups(self):
        self.gen.set_file_chunk_groups('/foo', [1, 2, 3])
        self.assertEqual(self.gen.get_file_chunk_groups(self.genid, '/foo'), 
                         [1, 2, 3])

