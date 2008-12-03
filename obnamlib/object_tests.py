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


class ObjectTests(unittest.TestCase):

    def test_sets_kind_correctly(self):
        obj = obnamlib.Object(obnamlib.GEN, "id")
        self.assertEqual(obj.kind, obnamlib.GEN)

    def test_sets_id_correctly(self):
        obj = obnamlib.Object(obnamlib.GEN, "id")
        self.assertEqual(obj.id, "id")

    def test_sets_component_to_empty_list_initially(self):
        obj = obnamlib.Object(obnamlib.GEN, "id")
        self.assertEqual(obj.components, [])

    def test_finds_nothing_by_kind_when_there_are_no_children(self):
        obj = obnamlib.Object(obnamlib.GEN, "id")
        self.assertEqual(obj.find(kind=obnamlib.FILENAME), [])

    def test_finds_by_kind(self):
        name = obnamlib.Component(kind=obnamlib.FILENAME)
        name.string = "foo"

        obj = obnamlib.Object(obnamlib.GEN, "id")
        obj.components.append(name)

        self.assertEqual(obj.find(kind=obnamlib.FILENAME), [name])

    def test_extracts_by_kind(self):
        name = obnamlib.Component(kind=obnamlib.FILENAME)
        name.string = "foo"

        obj = obnamlib.Object(obnamlib.GEN, "id")
        obj.components.append(name)

        obj.extract(kind=obnamlib.FILENAME)

        self.assertEqual(obj.components, [])
