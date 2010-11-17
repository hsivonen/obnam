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

    def test_sets_is_checkpoint(self):
        self.gen.require_forest()
        self.gen.start_generation(current_time=lambda: 12765)
        genid = self.gen.get_generation_id(self.gen.curgen)
        self.gen.set_current_generation_is_checkpoint(True)
        self.assert_(self.gen.get_is_checkpoint(genid))

    def test_unsets_is_checkpoint(self):
        self.gen.require_forest()
        self.gen.start_generation(current_time=lambda: 12765)
        genid = self.gen.get_generation_id(self.gen.curgen)
        self.gen.set_current_generation_is_checkpoint(True)
        self.gen.set_current_generation_is_checkpoint(False)
        self.assertFalse(self.gen.get_is_checkpoint(genid))

