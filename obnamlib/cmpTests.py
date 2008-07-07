# Copyright (C) 2006, 2007, 2008  Lars Wirzenius <liw@iki.fi>
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


"""Unit tests for obnamlib.cmp."""


import os
import unittest


import obnamlib


class ComponentKindNameTests(unittest.TestCase):

    def test(self):
        t = obnamlib.cmp.kind_name
        c = obnamlib.cmp
        self.failUnlessEqual(t(-12765), "UNKNOWN")

        names = (
            "OBJID",
            "OBJKIND",
            "BLKID",
            "FILECHUNK",
            "OBJECT",
            "OBJMAP",
            "CONTREF",
            "NAMEIPAIR",
            "FILENAME",
            "SIGDATA",
            "SIGREF",
            "GENREF",
            "OBJREF",
            "BLOCKREF",
            "MAPREF",
            "FILEPARTREF",
            "FORMATVERSION",
            "FILE",
            "FILELISTREF",
            "CONTMAPREF",
            "DELTAREF",
            "DELTADATA",
            "STAT",
            "GENSTART",
            "GENEND",
            "DELTAPARTREF",
            "DIRREF",
            "FILEGROUPREF",
            "SNAPSHOTGEN",
        )
        
        for name in names:
            self.failUnlessEqual(t(getattr(c, name)), name)


class RefComponentTests(unittest.TestCase):

    def test(self):
        kinds = obnamlib.cmp._component_kinds
        for kind in kinds:
            self.failUnlessEqual(kinds[kind][1].endswith("REF"),
                                 obnamlib.cmp.kind_is_reference(kind))


class CreateComponentTests(unittest.TestCase):

    def testCreateLeaf(self):
        c = obnamlib.cmp.Component(1, "pink")
        self.failIfEqual(c, None)
        self.failUnlessEqual(c.get_kind(), 1)
        self.failUnlessEqual(c.get_string_value(), "pink")
        self.failUnlessEqual(c.is_composite(), False)

    def testCreateComposite(self):
        leaf1 = obnamlib.cmp.Component(1, "pink")
        leaf2 = obnamlib.cmp.Component(2, "pretty")
        c = obnamlib.cmp.Component(3, [leaf1, leaf2])
        self.failUnlessEqual(c.get_kind(), 3)
        self.failUnlessEqual(c.is_composite(), True)
        self.failUnlessEqual(c.get_subcomponents(), [leaf1, leaf2])


class ComponentParserTest(unittest.TestCase):

    def testDecodeEmptyString(self):
        parser = obnamlib.cmp.Parser("")
        self.failUnlessEqual(parser.decode(), None)

    def testDecodePlainComponent(self):
        c = obnamlib.cmp.Component(obnamlib.cmp.OBJID, "pink")
        encoded = c.encode()
        parser = obnamlib.cmp.Parser(encoded)
        c2 = parser.decode()
        self.failUnlessEqual(parser.pos, len(encoded))
        self.failUnlessEqual(encoded, c2.encode())

    def testDecodeCompositeComponent(self):
        subs = [obnamlib.cmp.Component(obnamlib.cmp.OBJID, str(i)) 
                for i in range(100)]
        c = obnamlib.cmp.Component(obnamlib.cmp.OBJECT, subs)
        encoded = c.encode()
        parser = obnamlib.cmp.Parser(encoded)
        c2 = parser.decode()
        self.failUnlessEqual(parser.pos, len(encoded))
        self.failUnlessEqual(encoded, c2.encode())

    def testDecodeAllEmptyString(self):
        parser = obnamlib.cmp.Parser("")
        self.failUnlessEqual(parser.decode_all(), [])

    def testDecodeAllPlainComponents(self):
        list = [obnamlib.cmp.Component(obnamlib.cmp.OBJID, str(i))
                for i in range(100)]
        encoded = "".join(c.encode() for c in list)

        parser = obnamlib.cmp.Parser(encoded)
        list2 = parser.decode_all()
        self.failUnlessEqual(parser.pos, len(encoded))

        encoded2 = "".join(c.encode() for c in list2)
        self.failUnlessEqual(encoded, encoded2)


class ComponentDecodeAllTests(unittest.TestCase):

    def remove_component(self, list, kind, value):
        self.failUnlessEqual(list[0].get_kind(), kind)
        self.failUnlessEqual(list[0].get_string_value(), value)
        del list[0]

    def testDecodeAll(self):
        c1 = obnamlib.cmp.Component(1, "pink")
        c2 = obnamlib.cmp.Component(2, "pretty")
        e1 = c1.encode()
        e2 = c2.encode()
        e = e1 + e2
        list = obnamlib.cmp.Parser(e).decode_all()
        self.remove_component(list, 1, "pink")
        self.remove_component(list, 2, "pretty")
        self.failUnlessEqual(list, [])


class ComponentFindTests(unittest.TestCase):

    def setUp(self):
        list = [(1, "pink"), (2, "pretty"), (3, "black"), (3, "box")]
        list += [(4, obnamlib.varint.encode(4))]
        list = [obnamlib.cmp.Component(a, b) for a, b in list]
        self.c = obnamlib.cmp.Component(42, list)

    def match(self, result, kind, value):
        self.failUnless(len(result) > 0)
        c = result[0]
        self.failUnlessEqual(c.get_kind(), kind)
        self.failUnlessEqual(c.get_string_value(), value)
        del result[0]

    def testFindAllOnes(self):
        result = self.c.find_by_kind(1)
        self.match(result, 1, "pink")
        self.failUnlessEqual(result, [])

    def testFindAllTwos(self):
        result = self.c.find_by_kind(2)
        self.match(result, 2, "pretty")
        self.failUnlessEqual(result, [])

    def testFindAllThrees(self):
        result = self.c.find_by_kind(3)
        self.match(result, 3, "black")
        self.match(result, 3, "box")
        self.failUnlessEqual(result, [])

    def testFindAllNones(self):
        result = self.c.find_by_kind(0)
        self.failUnlessEqual(result, [])

    def testFindFirstOne(self):
        result = [self.c.first_by_kind(1)]
        self.match(result, 1, "pink")
        self.failUnlessEqual(result, [])

    def testFindFirstTwo(self):
        result = [self.c.first_by_kind(2)]
        self.match(result, 2, "pretty")
        self.failUnlessEqual(result, [])

    def testFindFirstThree(self):
        result = [self.c.first_by_kind(3)]
        self.match(result, 3, "black")
        self.failUnlessEqual(result, [])

    def testFindFirstNone(self):
        result = self.c.first_by_kind(0)
        self.failUnlessEqual(result, None)

    def testFindAllStringOnes(self):
        result = self.c.find_strings_by_kind(1)
        self.failUnlessEqual(result, ["pink"])

    def testFindAllStringTwos(self):
        result = self.c.find_strings_by_kind(2)
        self.failUnlessEqual(result, ["pretty"])

    def testFindAllStringThrees(self):
        result = self.c.find_strings_by_kind(3)
        self.failUnlessEqual(result, ["black", "box"])

    def testFindAllStringNones(self):
        result = self.c.find_strings_by_kind(0)
        self.failUnlessEqual(result, [])

    def testFindFirstStringOne(self):
        result = self.c.first_string_by_kind(1)
        self.failUnlessEqual(result, "pink")

    def testFindFirstStringTwo(self):
        result = self.c.first_string_by_kind(2)
        self.failUnlessEqual(result, "pretty")

    def testFindFirstStringThree(self):
        result = self.c.first_string_by_kind(3)
        self.failUnlessEqual(result, "black")

    def testFindFirstStringNone(self):
        result = self.c.first_string_by_kind(0)
        self.failUnlessEqual(result, None)

    def testFindFirstVarintByKind(self):
        result = self.c.first_varint_by_kind(4)
        self.failUnlessEqual(result, 4)

    def testFindFirstVarintByKindWhenMissing(self):
        result = self.c.first_varint_by_kind(0)
        self.failUnlessEqual(result, None)


class FindTests(unittest.TestCase):

    def setUp(self):
        self.list = [(1, "pink"), (2, "pretty"), (3, "black"), (3, "box")]
        self.list = [obnamlib.cmp.Component(a, b) for a, b in self.list]

    def tearDown(self):
        del self.list

    def match(self, result, kind, value):
        self.failUnless(len(result) > 0)
        c = result[0]
        self.failUnlessEqual(c.get_kind(), kind)
        self.failUnlessEqual(c.get_string_value(), value)
        del result[0]

    def testFindAllOnes(self):
        result = obnamlib.cmp.find_by_kind(self.list, 1)
        self.match(result, 1, "pink")
        self.failUnlessEqual(result, [])

    def testFindAllTwos(self):
        result = obnamlib.cmp.find_by_kind(self.list, 2)
        self.match(result, 2, "pretty")
        self.failUnlessEqual(result, [])

    def testFindAllThrees(self):
        result = obnamlib.cmp.find_by_kind(self.list, 3)
        self.match(result, 3, "black")
        self.match(result, 3, "box")
        self.failUnlessEqual(result, [])

    def testFindAllNones(self):
        result = obnamlib.cmp.find_by_kind(self.list, 0)
        self.failUnlessEqual(result, [])

    def testFindFirstOne(self):
        result = [obnamlib.cmp.first_by_kind(self.list, 1)]
        self.match(result, 1, "pink")
        self.failUnlessEqual(result, [])

    def testFindFirstTwo(self):
        result = [obnamlib.cmp.first_by_kind(self.list, 2)]
        self.match(result, 2, "pretty")
        self.failUnlessEqual(result, [])

    def testFindFirstThree(self):
        result = [obnamlib.cmp.first_by_kind(self.list, 3)]
        self.match(result, 3, "black")
        self.failUnlessEqual(result, [])

    def testFindFirstNone(self):
        result = obnamlib.cmp.first_by_kind(self.list, 0)
        self.failUnlessEqual(result, None)

    def testFindAllStringOnes(self):
        result = obnamlib.cmp.find_strings_by_kind(self.list, 1)
        self.failUnlessEqual(result, ["pink"])

    def testFindAllStringTwos(self):
        result = obnamlib.cmp.find_strings_by_kind(self.list, 2)
        self.failUnlessEqual(result, ["pretty"])

    def testFindAllStringThrees(self):
        result = obnamlib.cmp.find_strings_by_kind(self.list, 3)
        self.failUnlessEqual(result, ["black", "box"])

    def testFindAllStringNones(self):
        result = obnamlib.cmp.find_strings_by_kind(self.list, 0)
        self.failUnlessEqual(result, [])

    def testFindFirstStringOne(self):
        result = obnamlib.cmp.first_string_by_kind(self.list, 1)
        self.failUnlessEqual(result, "pink")

    def testFindFirstStringTwo(self):
        result = obnamlib.cmp.first_string_by_kind(self.list, 2)
        self.failUnlessEqual(result, "pretty")

    def testFindFirstStringThree(self):
        result = obnamlib.cmp.first_string_by_kind(self.list, 3)
        self.failUnlessEqual(result, "black")

    def testFindFirstStringNone(self):
        result = obnamlib.cmp.first_string_by_kind(self.list, 0)
        self.failUnlessEqual(result, None)


class GetVarintVAlueTest(unittest.TestCase):

    def test(self):
        c = obnamlib.cmp.Component(1, obnamlib.varint.encode(12765))
        self.failUnlessEqual(c.get_varint_value(), 12765)


class FindVarintTests(unittest.TestCase):

    def test(self):
        values = range(0, 1024, 17)

        list = []
        for i in values:
            encoded = obnamlib.varint.encode(i)
            c = obnamlib.cmp.Component(i, encoded)
            list.append(c)

        for i in values:
            self.failUnlessEqual(obnamlib.cmp.first_varint_by_kind(list, i), i)
        self.failUnlessEqual(obnamlib.cmp.first_varint_by_kind(list, -1), None)


class StatTests(unittest.TestCase):

    def testEncodeDecode(self):
        st1 = os.stat("Makefile")
        stat = obnamlib.cmp.create_stat_component(st1)
        st2 = obnamlib.cmp.parse_stat_component(stat)
        
        names1 = [x for x in dir(st1) if x.startswith("st_")]
        names2 = [x for x in dir(st2) if x.startswith("st_")]
        names1.sort()
        names2.sort()
        self.failUnlessEqual(names1, names2)
        for name in names1:
            self.failUnlessEqual(st1.__getattribute__(name),
                                 st2.__getattribute__(name))
