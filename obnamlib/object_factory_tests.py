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


class ObjectFactoryTests(unittest.TestCase):

    def setUp(self):
        self.factory = obnamlib.ObjectFactory()
        self.encoded = "2\n4\nid3\n8\n11\n3\n92\nfoo"

    def test_sets_id_to_a_string_value(self):
        obj = self.factory.new_object(obnamlib.GEN)
        self.assertEqual(type(obj.id), str)

    def test_sets_id_to_unique_value(self):
        obj1 = self.factory.new_object(obnamlib.GEN)
        obj2 = self.factory.new_object(obnamlib.GEN)
        self.assertNotEqual(obj1.id, obj2.id)

    def test_creates_new_object_with_desired_kind(self):
        obj = self.factory.new_object(kind=obnamlib.FILENAME)
        self.assertEqual(obj.kind, obnamlib.FILENAME)

    def test_encodes_empty_string_component_correctly(self):
        cmp = obnamlib.Component(obnamlib.FILENAME)
        self.assertEqual(self.factory.encode_component(cmp),
                         "0\n%d\n" % obnamlib.FILENAME)

    def test_encodes_string_component_correctly(self):
        cmp = obnamlib.Component(obnamlib.FILENAME)
        cmp.string = "foo"
        self.assertEqual(self.factory.encode_component(cmp),
                         "3\n%d\nfoo" % obnamlib.FILENAME)

    def test_encodes_ref_component_correctly(self):
        cmp = obnamlib.Component(obnamlib.CONTREF)
        cmp.string = "foo"
        self.assertEqual(self.factory.encode_component(cmp),
                         "3\n%d\nfoo" % obnamlib.CONTREF)

    def test_encodes_composite_component_correctly(self):
        name = obnamlib.Component(obnamlib.FILENAME)
        name.string = "foo"

        cmp = obnamlib.Component(obnamlib.OBJECT)
        cmp.children.append(name)

        self.assertEqual(self.factory.encode_component(cmp),
                         "8\n%d\n3\n%d\nfoo" % 
                         (obnamlib.OBJECT, obnamlib.FILENAME))

    def test_decodes_string_component_correctly(self):
        cmp, pos = self.factory.decode_component(self.encoded, 0)
        self.assertEqual(pos, 6)
        self.assertEqual(cmp.kind, obnamlib.OBJID)
        self.assertEqual(cmp.string, "id")

    def test_decodes_composite_component_correctly(self):
        name = obnamlib.Component(kind=obnamlib.FILENAME)
        name.string = "foo"

        cmp = obnamlib.Component(kind=obnamlib.OBJECT)
        cmp.children.append(name)

        encoded = self.factory.encode_component(cmp)

        decoded, pos = self.factory.decode_component(encoded, 0)
        self.assertEqual(cmp.kind, decoded.kind)
        self.assertEqual(pos, len(encoded))
        self.assertEqual(cmp.children[0].kind, name.kind)
        self.assertEqual(cmp.children[0].string, name.string)

    def test_decodes_all_components_correctly(self):
        list = self.factory.decode_all_components(self.encoded)
        self.assertEqual([c.kind for c in list],
                         [obnamlib.OBJID, obnamlib.OBJKIND, 
                          obnamlib.FILENAME])

    def test_encodes_empty_object_correctly(self):
        obj = self.factory.new_object(kind=obnamlib.FILEGROUP)
        obj.id = "id"
        self.assertEqual(self.factory.encode_object(obj), 
                         "2\n4\nid3\n8\n11\n")

    def test_encodes_object_correctly(self):
        name = obnamlib.Component(obnamlib.FILENAME)
        name.string = "foo"

        obj = self.factory.new_object(kind=obnamlib.FILEGROUP)
        obj.id = "id"
        obj.components.append(name)

        self.assertEqual(self.factory.encode_object(obj), self.encoded)

    def test_decoding_returns_correct_object(self):
        obj = self.factory.decode_object(self.encoded)
        self.assertEqual(obj.id, "id")
        self.assertEqual(obj.kind, obnamlib.FILEGROUP)
        self.assertEqual(len(obj.components), 1)
        self.assertEqual(obj.components[0].kind, obnamlib.FILENAME)
        self.assertEqual(obj.components[0].string, "foo")
