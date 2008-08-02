# Copyright (C) 2006  Lars Wirzenius <liw@iki.fi>
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


"""Unit tests for obnamlib.map."""


import unittest


import obnamlib


class ObjectMappingTests(unittest.TestCase):

    def testInvalidBlockRaisesException(self):
        m = obnamlib.map.create()
        self.failUnlessRaises(obnamlib.obj.BlockWithoutCookie,
                              obnamlib.map.decode_block, m, "pink")

    def testEmpty(self):
        m = obnamlib.map.create()
        self.failUnlessEqual(obnamlib.map.count(m), 0)

    def testGetNonexisting(self):
        m = obnamlib.map.create()
        self.failUnlessEqual(obnamlib.map.get(m, "pink"), None)

    def testAddOneMapping(self):
        m = obnamlib.map.create()
        obnamlib.map.add(m, "pink", "pretty")
        self.failUnlessEqual(obnamlib.map.count(m), 1)
        
        self.failUnlessEqual(obnamlib.map.get(m, "pink"), "pretty")

    def testAddTwoMappings(self):
        m = obnamlib.map.create()
        obnamlib.map.add(m, "pink", "pretty")
        self.failUnlessRaises(AssertionError, obnamlib.map.add,
                              m, "pink", "beautiful")

    def testGetNewMappings(self):
        m = obnamlib.map.create()
        self.failUnlessEqual(obnamlib.map.get_new(m), [])
        obnamlib.map.add(m, "pink", "pretty")
        self.failUnlessEqual(obnamlib.map.get_new(m), ["pink"])
        obnamlib.map.reset_new(m)
        self.failUnlessEqual(obnamlib.map.get_new(m), [])
        obnamlib.map.add(m, "black", "beautiful")
        self.failUnlessEqual(obnamlib.map.get_new(m), ["black"])

    def testMappingEncodings(self):
        # Set up a mapping
        m = obnamlib.map.create()
        
        # It's empty; make sure encoding new ones returns an empty list
        list = obnamlib.map.encode_new(m)
        self.failUnlessEqual(list, [])

        # Add a mapping
        obnamlib.map.add(m, "pink", "pretty")

        # Encode the new mapping, make sure that goes well
        list = obnamlib.map.encode_new(m)
        self.failUnlessEqual(len(list), 1)
        
        # Make sure the encoding is correct
        list2 = obnamlib.cmp.Parser(list[0]).decode_all()
        self.failUnlessEqual(len(list2), 1)
        self.failUnlessEqual(list2[0].kind, obnamlib.cmp.OBJMAP)
        
        list3 = list2[0].subcomponents
        self.failUnlessEqual(len(list3), 2)
        self.failUnlessEqual(list3[0].kind, obnamlib.cmp.BLOCKREF)
        self.failUnlessEqual(list3[0].str, "pretty")
        self.failUnlessEqual(list3[1].kind, obnamlib.cmp.OBJREF)
        self.failUnlessEqual(list3[1].str, "pink")

        # Now try decoding with the official function
        block = obnamlib.map.encode_new_to_block(m, "black")
        m2 = obnamlib.map.create()
        obnamlib.map.decode_block(m2, block)
        self.failUnlessEqual(obnamlib.map.count(m2), 1)
        self.failUnlessEqual(obnamlib.map.get(m2, "pink"), "pretty")

    def testMappingEncodingsForTwoInOneBlock(self):
        m = obnamlib.map.create()
        
        obnamlib.map.add(m, "pink", "pretty")
        obnamlib.map.add(m, "black", "pretty")

        list = obnamlib.map.encode_new(m)
        self.failUnlessEqual(len(list), 1)
        
        block = obnamlib.map.encode_new_to_block(m, "box")
        m2 = obnamlib.map.create()
        obnamlib.map.decode_block(m2, block)
        self.failUnlessEqual(obnamlib.map.count(m), obnamlib.map.count(m2))
        self.failUnlessEqual(obnamlib.map.get(m2, "pink"), "pretty")
        self.failUnlessEqual(obnamlib.map.get(m2, "black"), "pretty")
