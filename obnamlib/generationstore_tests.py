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

