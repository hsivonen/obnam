# Copyright (C) 2008  Lars Wirzenius <liw@liw.fi>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.


import unittest

import obnamlib


class FileGroupTests(unittest.TestCase):

    def setUp(self):
        self.fg = obnamlib.FileGroup("fg")
        self.stat_result = obnamlib.make_stat(st_size=1, st_mode=2)
        self.fg.add_file("foo", self.stat_result, "contref", "sigref", 
                         "deltaref")
        
    def test_has_no_files_initially(self):
        fg = obnamlib.FileGroup("fg")
        self.assertEqual(fg.names, [])

    def test_adds_file_correctly(self):
        self.assertEqual(self.fg.names, ["foo"])

    def test_get_file_raises_notfound_if_file_does_not_exist(self):
        self.assertRaises(obnamlib.NotFound, self.fg.get_file, "notfound")

    def test_gets_file_correctly(self):
        self.assertEqual(self.fg.get_file("foo"), 
                         (self.stat_result, "contref", "sigref", "deltaref"))

    def test_gets_stat_correctly(self):
        self.assertEqual(self.fg.get_stat("foo"), self.stat_result)

    def test_encodes_stat_result_internally(self):
        file = self.fg.files[0]
        stat = file.first(kind=obnamlib.STAT)
        self.assertEqual(type(stat), obnamlib.Component)
