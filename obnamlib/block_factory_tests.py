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


class BlockFactoryTests(unittest.TestCase):

    def setUp(self):
        self.factory = obnamlib.BlockFactory()

    def test_refuses_empty_string(self):
        self.assertRaises(obnamlib.Exception, self.factory.decode_block, "")

    def test_refuses_block_that_does_not_start_with_cookie(self):
        self.assertRaises(obnamlib.Exception, self.factory.decode_block, "foo")

    def test_refuses_block_with_bad_component(self):
        c = obnamlib.FileName("foo")
        of = obnamlib.ObjectFactory()
        s = self.factory.BLOCK_COOKIE + of.encode_component(c)
        self.assertRaises(obnamlib.Exception, self.factory.decode_block, s)

    def test_handles_empty_block_correctly(self):
        encoded = self.factory.encode_block("id", [], {})
        block_id, objects, mappings = self.factory.decode_block(encoded)
        self.assertEqual(block_id, "id")
        self.assertEqual(objects, [])
        self.assertEqual(mappings, {})

    def test_creates_mapping_components_correctly(self):
        orig_mappings = { "foo-object": "foo-block",
                          "bar-object": "foo-block",
                          "foobar-object": "bar-block",
                          }
        components = self.factory.mappings_to_components(orig_mappings)
        self.assertEqual(len(components), 2)
        self.assertEqual(components[0].first_string(kind=obnamlib.BLOCKREF),
                         "foo-block")
        self.assertEqual(components[0].find_strings(kind=obnamlib.OBJREF),
                         ["foo-object", "bar-object"])
        self.assertEqual(components[1].first_string(kind=obnamlib.BLOCKREF),
                         "bar-block")
        self.assertEqual(components[1].find_strings(kind=obnamlib.OBJREF),
                         ["foobar-object"])

    def test_handles_mappings_correctly(self):
        orig_mappings = { "foo-object": "foo-block",
                          "bar-object": "foo-block",
                          "foobar-object": "bar-block",
                          }
        encoded = self.factory.encode_block("id", [], orig_mappings)
        block_id, objects, mappings = self.factory.decode_block(encoded)
        self.assertEqual(block_id, "id")
        self.assertEqual(objects, [])
        self.assertEqual(mappings, orig_mappings)

    def test_handles_objects_correctly(self):
        obj = obnamlib.Object(id="foo")
        obj.kind = obnamlib.GEN
        encoded = self.factory.encode_block("id", [obj], {})
        block_id, objects, mappings = self.factory.decode_block(encoded)
        self.assertEqual(block_id, "id")
        self.assertEqual(len(objects), 1)
        self.assertEqual(objects[0].id, obj.id)
        self.assertEqual(objects[0].kind, obj.kind)
        self.assertEqual(mappings, {})
