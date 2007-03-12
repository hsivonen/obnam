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


"""Unit tests for obnam.cmp."""


import os
import unittest


import obnam


class ComponentKindNameTests(unittest.TestCase):

    def test(self):
        t = obnam.cmp.kind_name
        c = obnam.cmp
        self.failUnlessEqual(t(-12765), "UNKNOWN")
        self.failUnlessEqual(t(c.OBJID), "OBJID")
        self.failUnlessEqual(t(c.OBJKIND), "OBJKIND")
        self.failUnlessEqual(t(c.BLKID), "BLKID")
        self.failUnlessEqual(t(c.FILECHUNK), "FILECHUNK")
        self.failUnlessEqual(t(c.OBJECT), "OBJECT")
        self.failUnlessEqual(t(c.OBJMAP), "OBJMAP")
        self.failUnlessEqual(t(c.CONTREF), "CONTREF")
        self.failUnlessEqual(t(c.NAMEIPAIR), "NAMEIPAIR")
        self.failUnlessEqual(t(c.FILENAME), "FILENAME")
        self.failUnlessEqual(t(c.SIGDATA), "SIGDATA")
        self.failUnlessEqual(t(c.SIGREF), "SIGREF")
        self.failUnlessEqual(t(c.GENREF), "GENREF")
        self.failUnlessEqual(t(c.OBJREF), "OBJREF")
        self.failUnlessEqual(t(c.BLOCKREF), "BLOCKREF")
        self.failUnlessEqual(t(c.MAPREF), "MAPREF")
        self.failUnlessEqual(t(c.FILEPARTREF), "FILEPARTREF")
        self.failUnlessEqual(t(c.FORMATVERSION), "FORMATVERSION")
        self.failUnlessEqual(t(c.FILE), "FILE")
        self.failUnlessEqual(t(c.FILELISTREF), "FILELISTREF")
        self.failUnlessEqual(t(c.CONTMAPREF), "CONTMAPREF")
        self.failUnlessEqual(t(c.DELTAREF), "DELTAREF")
        self.failUnlessEqual(t(c.DELTADATA), "DELTADATA")
        self.failUnlessEqual(t(c.STAT), "STAT")
        self.failUnlessEqual(t(c.GENSTART), "GENSTART")
        self.failUnlessEqual(t(c.GENEND), "GENEND")
        self.failUnlessEqual(t(c.DELTAPARTREF), "DELTAPARTREF")


class RefComponentTests(unittest.TestCase):

    def test(self):
        kinds = obnam.cmp._component_kinds
        for kind in kinds:
            self.failUnlessEqual(kinds[kind][1].endswith("REF"),
                                 obnam.cmp.kind_is_reference(kind))


class CreateComponentTests(unittest.TestCase):

    def testCreateLeaf(self):
        c = obnam.cmp.create(1, "pink")
        self.failIfEqual(c, None)
        self.failUnlessEqual(c.get_kind(), 1)
        self.failUnlessEqual(c.get_string_value(), "pink")
        self.failUnlessEqual(c.is_composite(), False)

    def testCreateComposite(self):
        leaf1 = obnam.cmp.create(1, "pink")
        leaf2 = obnam.cmp.create(2, "pretty")
        c = obnam.cmp.create(3, [leaf1, leaf2])
        self.failUnlessEqual(c.get_kind(), 3)
        self.failUnlessEqual(c.is_composite(), True)
        self.failUnlessEqual(c.get_subcomponents(), [leaf1, leaf2])


class ComponentEncodingDecodingTests(unittest.TestCase):

    def doit(self, c_kind, data):
        c = obnam.cmp.create(c_kind, data)
        encoded = obnam.cmp.encode(c)
        (c2, pos) = obnam.cmp.decode(encoded, 0)
        encoded2 = obnam.cmp.encode(c2)
        self.failUnlessEqual(encoded, encoded2)
        self.failUnlessEqual(c.get_kind(), c2.get_kind())
        self.failUnlessEqual(c.is_composite(), c2.is_composite())
        self.failUnlessEqual(c.is_composite(), type(data) == type([]))
        if not c.is_composite():
            self.failUnlessEqual(c.get_string_value(),
                                 c2.get_string_value())
        self.failUnlessEqual(pos, len(encoded))

    def testEmpty(self):
        self.doit(1, "")

    def testNonempty(self):
        self.doit(2, "hello, world\0this is fun")

    def testEmptyComposite(self):
        self.doit(obnam.cmp.OBJECT, [])

    def testNonemptyComposite(self):
        c1 = obnam.cmp.create(1, "pink")
        c2 = obnam.cmp.create(2, "pretty")
        self.doit(obnam.cmp.OBJECT, [c1, c2])


class ComponentDecodeAllTests(unittest.TestCase):

    def remove_component(self, list, kind, value):
        self.failUnlessEqual(list[0].get_kind(), kind)
        self.failUnlessEqual(list[0].get_string_value(), value)
        del list[0]

    def testDecodeAll(self):
        c1 = obnam.cmp.create(1, "pink")
        c2 = obnam.cmp.create(2, "pretty")
        e1 = obnam.cmp.encode(c1)
        e2 = obnam.cmp.encode(c2)
        e = e1 + e2
        list = obnam.cmp.decode_all(e, 0)
        self.remove_component(list, 1, "pink")
        self.remove_component(list, 2, "pretty")
        self.failUnlessEqual(list, [])


class FindTests(unittest.TestCase):

    def setUp(self):
        self.list = [(1, "pink"), (2, "pretty"), (3, "black"), (3, "box")]
        self.list = [obnam.cmp.create(a, b) for a, b in self.list]

    def tearDown(self):
        del self.list

    def match(self, result, kind, value):
        self.failUnless(len(result) > 0)
        c = result[0]
        self.failUnlessEqual(c.get_kind(), kind)
        self.failUnlessEqual(c.get_string_value(), value)
        del result[0]

    def testFindAllOnes(self):
        result = obnam.cmp.find_by_kind(self.list, 1)
        self.match(result, 1, "pink")
        self.failUnlessEqual(result, [])

    def testFindAllTwos(self):
        result = obnam.cmp.find_by_kind(self.list, 2)
        self.match(result, 2, "pretty")
        self.failUnlessEqual(result, [])

    def testFindAllThrees(self):
        result = obnam.cmp.find_by_kind(self.list, 3)
        self.match(result, 3, "black")
        self.match(result, 3, "box")
        self.failUnlessEqual(result, [])

    def testFindAllNones(self):
        result = obnam.cmp.find_by_kind(self.list, 0)
        self.failUnlessEqual(result, [])

    def testFindFirstOne(self):
        result = [obnam.cmp.first_by_kind(self.list, 1)]
        self.match(result, 1, "pink")
        self.failUnlessEqual(result, [])

    def testFindFirstTwo(self):
        result = [obnam.cmp.first_by_kind(self.list, 2)]
        self.match(result, 2, "pretty")
        self.failUnlessEqual(result, [])

    def testFindFirstThree(self):
        result = [obnam.cmp.first_by_kind(self.list, 3)]
        self.match(result, 3, "black")
        self.failUnlessEqual(result, [])

    def testFindFirstNone(self):
        result = obnam.cmp.first_by_kind(self.list, 0)
        self.failUnlessEqual(result, None)

    def testFindAllStringOnes(self):
        result = obnam.cmp.find_strings_by_kind(self.list, 1)
        self.failUnlessEqual(result, ["pink"])

    def testFindAllStringTwos(self):
        result = obnam.cmp.find_strings_by_kind(self.list, 2)
        self.failUnlessEqual(result, ["pretty"])

    def testFindAllStringThrees(self):
        result = obnam.cmp.find_strings_by_kind(self.list, 3)
        self.failUnlessEqual(result, ["black", "box"])

    def testFindAllStringNones(self):
        result = obnam.cmp.find_strings_by_kind(self.list, 0)
        self.failUnlessEqual(result, [])

    def testFindFirstStringOne(self):
        result = obnam.cmp.first_string_by_kind(self.list, 1)
        self.failUnlessEqual(result, "pink")

    def testFindFirstStringTwo(self):
        result = obnam.cmp.first_string_by_kind(self.list, 2)
        self.failUnlessEqual(result, "pretty")

    def testFindFirstStringThree(self):
        result = obnam.cmp.first_string_by_kind(self.list, 3)
        self.failUnlessEqual(result, "black")

    def testFindFirstStringNone(self):
        result = obnam.cmp.first_string_by_kind(self.list, 0)
        self.failUnlessEqual(result, None)


class GetVarintVAlueTest(unittest.TestCase):

    def test(self):
        c = obnam.cmp.create(1, obnam.varint.encode(12765))
        self.failUnlessEqual(c.get_varint_value(), 12765)


class FindVarintTests(unittest.TestCase):

    def test(self):
        list = []
        for i in range(1024):
            encoded = obnam.varint.encode(i)
            c = obnam.cmp.create(i, encoded)
            list.append(c)

        for i in range(1024):
            self.failUnlessEqual(obnam.cmp.first_varint_by_kind(list, i), 
                                 i)
        self.failUnlessEqual(obnam.cmp.first_varint_by_kind(list, -1), None)


class StatTests(unittest.TestCase):

    def testEncodeDecode(self):
        st1 = os.stat("Makefile")
        stat = obnam.cmp.create_stat_component(st1)
        st2 = obnam.cmp.parse_stat_component(stat)
        
        names1 = [x for x in dir(st1) if x.startswith("st_")]
        names2 = [x for x in dir(st2) if x.startswith("st_")]
        names1.sort()
        names2.sort()
        self.failUnlessEqual(names1, names2)
        for name in names1:
            self.failUnlessEqual(st1.__getattribute__(name),
                                 st2.__getattribute__(name))
