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


class ChunkListTests(unittest.TestCase):

    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        fs = obnamlib.LocalFS(self.tempdir)
        self.list = obnamlib.ChunkList(fs, 
                                       obnamlib.DEFAULT_NODE_SIZE,
                                       obnamlib.DEFAULT_UPLOAD_QUEUE_SIZE,
                                       obnamlib.DEFAULT_LRU_SIZE)

    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def test_raises_keyerror_for_missing_chunk(self):
        self.assertRaises(KeyError, self.list.get_checksum, 0)
        
    def test_adds_chunk(self):
        self.list.add(0, 'checksum')
        self.assertEqual(self.list.get_checksum(0), 'checksum')

    def test_removes_chunk(self):
        self.list.add(0, 'checksum')
        self.list.remove(0)
        self.assertRaises(KeyError, self.list.get_checksum, 0)

