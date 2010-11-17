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


import hashlib
import shutil
import tempfile
import unittest

import obnamlib


class ChecksumTreeTests(unittest.TestCase):

    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        fs = obnamlib.LocalFS(self.tempdir)
        self.checksum = hashlib.md5('foo').digest()
        self.tree = obnamlib.ChecksumTree(fs, 'x', len(self.checksum), 
                                          obnamlib.DEFAULT_NODE_SIZE,
                                          obnamlib.DEFAULT_UPLOAD_QUEUE_SIZE,
                                          obnamlib.DEFAULT_LRU_SIZE)

    def tearDown(self):
        self.tree.commit()
        shutil.rmtree(self.tempdir)

    def test_is_empty_initially(self):
        self.assertEqual(self.tree.find(self.checksum), [])

    def test_finds_checksums(self):
        self.tree.add(self.checksum, 1)
        self.tree.add(self.checksum, 2)
        self.assertEqual(sorted(self.tree.find(self.checksum)), [1, 2])

    def test_finds_only_the_right_checksums(self):
        self.tree.add(self.checksum, 1)
        self.tree.add(self.checksum, 2)
        self.tree.add(hashlib.md5('bar').digest(), 3)
        self.assertEqual(sorted(self.tree.find(self.checksum)), [1, 2])

    def test_removes_checksum(self):
        self.tree.add(self.checksum, 1)
        self.tree.add(self.checksum, 2)
        self.tree.remove(self.checksum, 2)
        self.assertEqual(self.tree.find(self.checksum), [1])

    def test_adds_same_id_only_once(self):
        self.tree.add(self.checksum, 1)
        self.tree.add(self.checksum, 1)
        self.assertEqual(self.tree.find(self.checksum), [1])

