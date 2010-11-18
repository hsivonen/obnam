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


class ChunkGroupTreeTests(unittest.TestCase):

    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        fs = obnamlib.LocalFS(self.tempdir)
        self.tree = obnamlib.ChunkGroupTree(fs, 
                                            obnamlib.DEFAULT_NODE_SIZE, 
                                            obnamlib.DEFAULT_UPLOAD_QUEUE_SIZE,
                                            obnamlib.DEFAULT_LRU_SIZE)

    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def test_is_empty_initially(self):
        self.assertEqual(self.tree.list_chunk_groups(), [])

    def test_no_chunks_for_nonexistent_group(self):
        self.assertEqual(self.tree.list_chunk_group_chunks(1), [])

    def test_chunk_group_does_not_exist_initially(self):
        self.assertFalse(self.tree.group_exists(1))

    def test_adds_chunk_group(self):
        self.tree.add(1, [1, 2, 3])
        self.assert_(self.tree.group_exists(1))
        self.assertEqual(self.tree.list_chunk_groups(), [1])
        self.assertEqual(self.tree.list_chunk_group_chunks(1), [1, 2, 3])

    def test_adds_two_chunk_groups(self):
        self.tree.add(1, [1, 2, 3])
        self.tree.add(2, [4, 5, 6])
        self.assertEqual(sorted(self.tree.list_chunk_groups()), [1, 2])
        self.assertEqual(self.tree.list_chunk_group_chunks(1), [1, 2, 3])
        self.assertEqual(self.tree.list_chunk_group_chunks(2), [4, 5, 6])

    def test_adds_chunk_group_with_duplicate_chunks(self):
        self.tree.add(1, [2, 2])
        self.assertEqual(self.tree.list_chunk_group_chunks(1), [2, 2])

    def test_adds_chunk_group_without_chunks(self):
        self.tree.add(1, [])
        self.assertEqual(self.tree.list_chunk_group_chunks(1), [])

    def test_removes_chunk_group(self):
        self.tree.add(1, [1, 2, 3])
        self.tree.remove(1)
        self.assertEqual(self.tree.list_chunk_groups(), [])

    def test_removed_chunk_group_no_longer_exists(self):
        self.tree.add(1, [1, 2, 3])
        self.tree.remove(1)
        self.assertFalse(self.tree.group_exists(1))

