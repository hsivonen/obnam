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


class GenTests(unittest.TestCase):

    def setUp(self):
        self.gen = obnamlib.Generation(id="id")

    def test_sets_dirrefs_to_empty_by_default(self):
        self.assertEqual(self.gen.dirrefs, [])

    def test_has_no_dirref_components_by_default(self):
        self.assertEqual(self.gen.find_strings(kind=obnamlib.DIRREF), [])

    def test_allows_appending_to_dirrefs(self):
        self.gen.dirrefs.append("foo")
        self.assertEqual(self.gen.dirrefs, ["foo"])

    def test_allows_plusequal_to_dirrefs(self):
        self.gen.dirrefs += ["foo"]
        self.assertEqual(self.gen.dirrefs, ["foo"])

    def test_sets_fgrefs_to_empty_by_default(self):
        self.assertEqual(self.gen.fgrefs, [])

    def test_has_no_fgref_components_by_default(self):
        self.assertEqual(self.gen.find_strings(kind=obnamlib.FILEGROUPREF), 
                         [])

    def test_allows_appending_to_fgrefs(self):
        self.gen.fgrefs.append("foo")
        self.assertEqual(self.gen.fgrefs, ["foo"])

    def test_allows_plusequal_to_fgrefs(self):
        self.gen.fgrefs += ["foo"]
        self.assertEqual(self.gen.fgrefs, ["foo"])

    def test_prepare_adds_dirrefs_to_components(self):
        self.gen.dirrefs += ["foo"]
        self.gen.prepare_for_encoding()
        self.assertEqual(self.gen.find_strings(kind=obnamlib.DIRREF), ["foo"])

    def test_prepare_adds_fgrefs_to_components(self):
        self.gen.fgrefs += ["foo"]
        self.gen.prepare_for_encoding()
        self.assertEqual(self.gen.find_strings(kind=obnamlib.FILEGROUPREF), 
                         ["foo"])

    def test_post_hook_extracts_stuff(self):
        gen = obnamlib.Generation(id="id")

        gen.components.append(obnamlib.DirRef("dir1"))
        gen.components.append(obnamlib.DirRef("dir2"))

        gen.components.append(obnamlib.FileGroupRef("fg1"))
        gen.components.append(obnamlib.FileGroupRef("fg2"))

        gen.post_decoding_hook()
        self.assertEqual(gen.dirrefs, ["dir1", "dir2"])
        self.assertEqual(gen.fgrefs, ["fg1", "fg2"])
