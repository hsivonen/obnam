# Copyright (C) 2006, 2008  Lars Wirzenius <liw@iki.fi>
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


"""Unit tests for mapping object to block identifiers."""


import unittest


import obnamlib


class MapTests(unittest.TestCase):

    def setUp(self):
        self.map = self.mocked_map()

    def mocked_map(self):
        map = obnamlib.Map(None)
        map.fetch_block = self.mock_fetch_block
        return map

    def create_map_block(self, map_block_id, tuples):
        temp = self.mocked_map()
        for object_id, block_id in tuples:
            temp[object_id] = block_id
        return temp.encode_new_to_block(map_block_id)

    def mock_fetch_block(self, context, block_id):
        return self.mock_block

    def testReturnsNoneForUnknownObjectId(self):
        self.assertEqual(self.map["pink"], None)

    def testSetsMapping(self):
        self.map["pink"] = "pretty"
        self.assertEqual(self.map["pink"], "pretty")

    def testWorksWithIn(self):
        self.map["pink"] = "pretty"
        self.assert_("pink" in self.map)

    def testWorksWithInWhenObjectIdNotInMapping(self):
        self.assertFalse("pink" in self.map)
        
    def testRaisesErrorIfSettingSameMappingTwice(self):
        self.map["pink"] = "pretty"
        self.assertRaises(Exception, self.map.__setitem__, "pink", "pretty")

    def testReturnsZeroLengthForEmptyMapping(self):
        self.assertEqual(len(self.map), 0)
        
    def testReturnsOneForLengthOfMappingWithOneKeySet(self):
        self.map["pink"] = "pretty"
        self.assertEqual(len(self.map), 1)

    def testInvalidBlockRaisesException(self):
        self.failUnlessRaises(obnamlib.obj.BlockWithoutCookie,
                              self.map.decode_block, "pink")

    def testReturnsNoNewMappingsInitially(self):
        self.assertEqual(self.map.get_new(), set())
        
    def testReturnsOneNewMappingAfterOneIsAdded(self):
        self.map["pink"] = "pretty"
        self.assertEqual(self.map.get_new(), set(["pink"]))

    def testReturnsNoNewMappingsAfterNewKeysHaveBeenReset(self):
        self.map["pink"] = "pretty"
        self.map.reset_new()
        self.assertEqual(self.map.get_new(), set())

    def testEncodesSingleNewKeyCorrectly(self):
        self.map["pink"] = "pretty"
        encoded = self.map.encode_new()
        self.assertEqual(len(encoded), 1)

        decoded = obnamlib.cmp.Parser(encoded[0]).decode_all()
        self.assertEqual(len(decoded), 1)

        c = decoded[0]
        self.assertEqual(c.kind, obnamlib.cmp.OBJMAP)
        self.assertEqual(c.first_string_by_kind(obnamlib.cmp.BLOCKREF),
                         "pretty")
        self.assertEqual(c.find_strings_by_kind(obnamlib.cmp.OBJREF),
                         ["pink"])

    def testEncodesAndDecodesBlockWithTwoMappingsCorrectly(self):
        self.map["pink"] = "pretty"
        self.map["black"] = "pretty"
        block = self.map.encode_new_to_block("beautiful")
        map2 = self.mocked_map()
        map2.decode_block(block)
        self.assertEqual(map2.get_new(), set())
        self.assertEqual(len(map2), 2)
        self.assertEqual(map2["pink"], "pretty")
        self.assertEqual(map2["black"], "pretty")
        
    def testSetsLoadedBlocksToEmptyInitially(self):
        self.assertEqual(self.map.loaded_blocks, set())
        
    def testDemandLoadsMappingCorrectly(self):
        self.mock_block = self.create_map_block("black", [("pink", "pretty")])
        self.map.load_from_blocks(["black"])
        self.assertEqual(self.map["pink"], "pretty")

    def testForgetsOldMappingsWhenTotalBecomesTooLarge(self):
        self.map.max = 2
        self.map["pink"] = "pretty"
        self.map["black"] = "beautiful"
        self.assertEqual(len(self.map), 2)
        self.map.reset_new()
        self.map["foo"] = "bar"
        self.assertEqual(len(self.map), 3)  # 2 old ones, plus new one
        self.map.reset_new()                # there's now 3 old ones
        self.map["foobar"] = "baz"
        self.assertEqual(len(self.map), 3)  # still 2 old ones, plus new one

