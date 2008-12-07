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


class FilePartTests(unittest.TestCase):

    def setUp(self):
        self.part = obnamlib.FilePart(id="id", data="data")

    def test_sets_id_correctly(self):
        self.assertEqual(self.part.id, "id")

    def test_sets_kind_correctly(self):
        self.assertEqual(self.part.kind, obnamlib.FILEPART)

    def test_sets_initial_data_correctly(self):
        self.assertEqual(self.part.data, "data")

    def test_sets_new_data_correctly(self):
        self.part.data = "newdata"
        self.assertEqual(self.part.data, "newdata")

    def test_sets_initial_data_to_empty_string_by_default(self):
        part = obnamlib.FilePart(id="id")
        self.assertEqual(part.data, "")
