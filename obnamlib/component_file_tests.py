# Copyright (C) 2009  Lars Wirzenius <liw@liw.fi>
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


class FileTests(unittest.TestCase):

    def setUp(self):
        self.stat = obnamlib.make_stat()
        self.owner = "owner"
        self.group = "group"
        self.file = obnamlib.File("filename", self.stat, "contref", "sigref",
                                  "deltaref", "target")
        self.none = obnamlib.File("filename", obnamlib.make_stat())

    def test_has_filename_attribute(self):
        self.assertEqual(self.file.filename, "filename")

    def test_has_stat_attribute(self):
        self.assertEqual(self.file.stat, self.stat)

    def test_has_owner_attribute(self):
        self.assertEqual(self.file.owner, self.owner)

    def test_has_group_attribute(self):
        self.assertEqual(self.file.group, self.group)

    def test_has_contref_attribute(self):
        self.assertEqual(self.file.contref, "contref")

    def test_has_sigref_attribute(self):
        self.assertEqual(self.file.sigref, "sigref")

    def test_has_deltaref_attribute(self):
        self.assertEqual(self.file.deltaref, "deltaref")

    def test_has_symlink_target_attribute(self):
        self.assertEqual(self.file.symlink_target, "target")

    def test_handles_None_as_contref_correctly(self):
        self.assertEqual(self.none.contref, None)

    def test_handles_None_as_sigref_correctly(self):
        self.assertEqual(self.none.sigref, None)

    def test_handles_None_as_deltaref_correctly(self):
        self.assertEqual(self.none.deltaref, None)

    def test_handles_None_as_symlink_target_correctly(self):
        self.assertEqual(self.none.symlink_target, None)
