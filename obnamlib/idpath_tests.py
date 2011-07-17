# Copyright 2011  Lars Wirzenius
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


import os
import shutil
import tempfile
import unittest

import obnamlib


class IdPathTests(unittest.TestCase):

    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        self.depth = 3
        self.idpath = obnamlib.IdPath(self.tempdir, self.depth)
    
    def tearDown(self):
        shutil.rmtree(self.tempdir)
    
    def test_returns_string(self):
        self.assertEqual(type(self.idpath.convert(1)), str)

    def test_starts_with_designated_path(self):
        path = self.idpath.convert(1)
        self.assert_(path.startswith(self.tempdir))

    def test_different_ids_return_different_values(self):
        path1 = self.idpath.convert(42)
        path2 = self.idpath.convert(1024)
        self.assertNotEqual(path1, path2)

    def test_same_id_returns_same_path(self):
        path1 = self.idpath.convert(42)
        path2 = self.idpath.convert(42)
        self.assertEqual(path1, path2)

    def test_uses_desired_depth(self):
        path = self.idpath.convert(1)
        subpath = path[len(self.tempdir + os.sep):]
        subdir = os.path.dirname(subpath)
        self.assertEqual(len(subdir.split(os.sep)), self.depth)

