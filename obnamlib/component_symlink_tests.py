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


class SymlinkTests(unittest.TestCase):

    def setUp(self):
        self.stat = obnamlib.make_stat()
        self.symlink = obnamlib.Symlink("filename", self.stat, "target")
        self.none = obnamlib.Symlink(None, None, None)

    def test_has_filename_attribute(self):
        self.assertEqual(self.symlink.filename, "filename")

    def test_has_stat_attribute(self):
        self.assertEqual(self.symlink.stat, self.stat)

    def test_has_target_attribute(self):
        self.assertEqual(self.symlink.target, "target")

    def test_handles_None_as_filename_correctly(self):
        self.assertEqual(self.none.filename, None)

    def test_handles_None_as_stat_correctly(self):
        self.assertEqual(self.none.stat, None)

    def test_handles_None_as_target_correctly(self):
        self.assertEqual(self.none.target, None)
