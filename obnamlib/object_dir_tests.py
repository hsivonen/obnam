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


import os
import unittest

import obnamlib


class DirTests(unittest.TestCase):

    def setUp(self):
        self.dir = obnamlib.Dir(id="id", name="name", 
                                stat=obnamlib.make_stat(),
                                dirrefs=["dir1", "dir2"],
                                fgrefs=["fg1", "fg2"])

    def test_sets_name_correctly(self):
        self.assertEqual(self.dir.name, "name")

    def test_sets_stat_correctly(self):
        self.assert_(isinstance(self.dir.stat, os.stat_result))

    def test_sets_dirrefs_correctly(self):
        self.assertEqual(self.dir.dirrefs, ["dir1", "dir2"])

    def test_sets_fgrefs_correctl(self):
        self.assertEqual(self.dir.fgrefs, ["fg1", "fg2"])

    def test_prepare_encodes_name(self):
        self.dir.prepare_for_encoding()
        self.assertEqual(self.dir.find_strings(kind=obnamlib.FILENAME), 
                         ["name"])

    def test_prepare_encodes_stat(self):
        self.dir.prepare_for_encoding()
        list = self.dir.find(kind=obnamlib.STAT)
        self.assertEqual(len(list), 1)
        st = obnamlib.decode_stat(list[0].string)
        self.assertEqual(st, obnamlib.make_stat())

    def test_prepare_encodes_dirrefs(self):
        self.dir.prepare_for_encoding()
        self.assertEqual(self.dir.find_strings(kind=obnamlib.DIRREF), 
                         ["dir1", "dir2"])

    def test_prepare_encodes_fgrefs(self):
        self.dir.prepare_for_encoding()
        self.assertEqual(self.dir.find_strings(kind=obnamlib.FILEGROUPREF), 
                         ["fg1", "fg2"])

    def test_post_hook_extracts_stuff(self):
        dir = obnamlib.Dir(id="id")

        c = obnamlib.Component(kind=obnamlib.FILENAME, string="foo")
        dir.components.append(c)

        encoded = obnamlib.encode_stat(obnamlib.make_stat())
        c = obnamlib.Component(kind=obnamlib.STAT, string=encoded)
        dir.components.append(c)

        c = obnamlib.Component(kind=obnamlib.DIRREF, string="dir1")
        dir.components.append(c)

        c = obnamlib.Component(kind=obnamlib.DIRREF, string="dir2")
        dir.components.append(c)

        c = obnamlib.Component(kind=obnamlib.FILEGROUPREF, string="fg1")
        dir.components.append(c)

        c = obnamlib.Component(kind=obnamlib.FILEGROUPREF, string="fg2")
        dir.components.append(c)

        dir.post_decoding_hook()
        self.assertEqual(dir.name, "foo")
        self.assertEqual(dir.stat, obnamlib.make_stat())
        self.assertEqual(dir.dirrefs, ["dir1", "dir2"])
        self.assertEqual(dir.fgrefs, ["fg1", "fg2"])
