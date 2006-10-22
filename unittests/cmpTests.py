"""Unit tests for wibbrlib.cmp."""


import os
import unittest


import wibbrlib


class ComponentKindNameTests(unittest.TestCase):

    def test(self):
        t = wibbrlib.cmp.kind_name
        c = wibbrlib.cmp
        self.failUnlessEqual(t(-12765), "CMP_UNKNOWN")
        self.failUnlessEqual(t(c.CMP_OBJID), "CMP_OBJID")
        self.failUnlessEqual(t(c.CMP_OBJKIND), "CMP_OBJKIND")
        self.failUnlessEqual(t(c.CMP_BLKID), "CMP_BLKID")
        self.failUnlessEqual(t(c.CMP_FILECHUNK), "CMP_FILECHUNK")
        self.failUnlessEqual(t(c.CMP_OBJECT), "CMP_OBJECT")
        self.failUnlessEqual(t(c.CMP_OBJMAP), "CMP_OBJMAP")
        self.failUnlessEqual(t(c.CMP_ST_MODE), "CMP_ST_MODE")
        self.failUnlessEqual(t(c.CMP_ST_INO), "CMP_ST_INO")
        self.failUnlessEqual(t(c.CMP_ST_DEV), "CMP_ST_DEV")
        self.failUnlessEqual(t(c.CMP_ST_NLINK), "CMP_ST_NLINK")
        self.failUnlessEqual(t(c.CMP_ST_UID), "CMP_ST_UID")
        self.failUnlessEqual(t(c.CMP_ST_GID), "CMP_ST_GID")
        self.failUnlessEqual(t(c.CMP_ST_SIZE), "CMP_ST_SIZE")
        self.failUnlessEqual(t(c.CMP_ST_ATIME), "CMP_ST_ATIME")
        self.failUnlessEqual(t(c.CMP_ST_MTIME), "CMP_ST_MTIME")
        self.failUnlessEqual(t(c.CMP_ST_CTIME), "CMP_ST_CTIME")
        self.failUnlessEqual(t(c.CMP_ST_BLOCKS), "CMP_ST_BLOCKS")
        self.failUnlessEqual(t(c.CMP_ST_BLKSIZE), "CMP_ST_BLKSIZE")
        self.failUnlessEqual(t(c.CMP_ST_RDEV), "CMP_ST_RDEV")
        self.failUnlessEqual(t(c.CMP_CONTREF), "CMP_CONTREF")
        self.failUnlessEqual(t(c.CMP_NAMEIPAIR), "CMP_NAMEIPAIR")
        self.failUnlessEqual(t(c.CMP_INODEREF), "CMP_INODEREF")
        self.failUnlessEqual(t(c.CMP_FILENAME), "CMP_FILENAME")
        self.failUnlessEqual(t(c.CMP_SIGDATA), "CMP_SIGDATA")
        self.failUnlessEqual(t(c.CMP_SIGREF), "CMP_SIGREF")
        self.failUnlessEqual(t(c.CMP_GENREF), "CMP_GENREF")
        self.failUnlessEqual(t(c.CMP_OBJREF), "CMP_OBJREF")
        self.failUnlessEqual(t(c.CMP_BLOCKREF), "CMP_BLOCKREF")
        self.failUnlessEqual(t(c.CMP_MAPREF), "CMP_MAPREF")
        self.failUnlessEqual(t(c.CMP_FILEPARTREF), "CMP_FILEPARTREF")
        self.failUnlessEqual(t(c.CMP_FORMATVERSION), "CMP_FORMATVERSION")


class RefComponentTests(unittest.TestCase):

    def test(self):
        kinds = wibbrlib.cmp._component_kinds
        for kind in kinds:
            self.failUnlessEqual(kinds[kind][1].endswith("REF"),
                                 wibbrlib.cmp.kind_is_reference(kind))


class CreateComponentTests(unittest.TestCase):

    def testCreateLeaf(self):
        c = wibbrlib.cmp.create(1, "pink")
        self.failIfEqual(c, None)
        self.failUnlessEqual(wibbrlib.cmp.get_kind(c), 1)
        self.failUnlessEqual(wibbrlib.cmp.get_string_value(c), "pink")
        self.failUnlessEqual(wibbrlib.cmp.is_composite(c), False)

    def testCreateComposite(self):
        leaf1 = wibbrlib.cmp.create(1, "pink")
        leaf2 = wibbrlib.cmp.create(2, "pretty")
        c = wibbrlib.cmp.create(3, [leaf1, leaf2])
        self.failUnlessEqual(wibbrlib.cmp.get_kind(c), 3)
        self.failUnlessEqual(wibbrlib.cmp.is_composite(c), True)
        self.failUnlessEqual(wibbrlib.cmp.get_subcomponents(c), 
                             [leaf1, leaf2])


class ComponentEncodingDecodingTests(unittest.TestCase):

    def doit(self, c_kind, data):
        c = wibbrlib.cmp.create(c_kind, data)
        encoded = wibbrlib.cmp.encode(c)
        (c2, pos) = wibbrlib.cmp.decode(encoded, 0)
        encoded2 = wibbrlib.cmp.encode(c2)
        self.failUnlessEqual(encoded, encoded2)
        self.failUnlessEqual(wibbrlib.cmp.get_kind(c), 
                             wibbrlib.cmp.get_kind(c2))
        self.failUnlessEqual(wibbrlib.cmp.is_composite(c), 
                             wibbrlib.cmp.is_composite(c2))
        self.failUnlessEqual(wibbrlib.cmp.is_composite(c),
                             type(data) == type([]))
        if not wibbrlib.cmp.is_composite(c):
            self.failUnlessEqual(wibbrlib.cmp.get_string_value(c),
                                 wibbrlib.cmp.get_string_value(c2))            
        self.failUnlessEqual(pos, len(encoded))

    def testEmpty(self):
        self.doit(1, "")

    def testNonempty(self):
        self.doit(2, "hello, world\0this is fun")

    def testEmptyComposite(self):
        self.doit(wibbrlib.cmp.CMP_OBJECT, [])

    def testNonemptyComposite(self):
        c1 = wibbrlib.cmp.create(1, "pink")
        c2 = wibbrlib.cmp.create(2, "pretty")
        self.doit(wibbrlib.cmp.CMP_OBJECT, [c1, c2])


class ComponentDecodeAllTests(unittest.TestCase):

    def remove_component(self, list, kind, value):
        self.failUnlessEqual(wibbrlib.cmp.get_kind(list[0]), kind)
        self.failUnlessEqual(wibbrlib.cmp.get_string_value(list[0]), 
                             value)
        del list[0]

    def testDecodeAll(self):
        c1 = wibbrlib.cmp.create(1, "pink")
        c2 = wibbrlib.cmp.create(2, "pretty")
        e1 = wibbrlib.cmp.encode(c1)
        e2 = wibbrlib.cmp.encode(c2)
        e = e1 + e2
        list = wibbrlib.cmp.decode_all(e, 0)
        self.remove_component(list, 1, "pink")
        self.remove_component(list, 2, "pretty")
        self.failUnlessEqual(list, [])


class FindTests(unittest.TestCase):

    def setUp(self):
        self.list = [(1, "pink"), (2, "pretty"), (3, "black"), (3, "box")]
        self.list = [wibbrlib.cmp.create(a, b) for a, b in self.list]

    def tearDown(self):
        del self.list

    def match(self, result, kind, value):
        self.failUnless(len(result) > 0)
        c = result[0]
        self.failUnlessEqual(wibbrlib.cmp.get_kind(c), kind)
        self.failUnlessEqual(wibbrlib.cmp.get_string_value(c), value)
        del result[0]

    def testFindAllOnes(self):
        result = wibbrlib.cmp.find_by_kind(self.list, 1)
        self.match(result, 1, "pink")
        self.failUnlessEqual(result, [])

    def testFindAllTwos(self):
        result = wibbrlib.cmp.find_by_kind(self.list, 2)
        self.match(result, 2, "pretty")
        self.failUnlessEqual(result, [])

    def testFindAllThrees(self):
        result = wibbrlib.cmp.find_by_kind(self.list, 3)
        self.match(result, 3, "black")
        self.match(result, 3, "box")
        self.failUnlessEqual(result, [])

    def testFindAllNones(self):
        result = wibbrlib.cmp.find_by_kind(self.list, 0)
        self.failUnlessEqual(result, [])

    def testFindFirstOne(self):
        result = [wibbrlib.cmp.first_by_kind(self.list, 1)]
        self.match(result, 1, "pink")
        self.failUnlessEqual(result, [])

    def testFindFirstTwo(self):
        result = [wibbrlib.cmp.first_by_kind(self.list, 2)]
        self.match(result, 2, "pretty")
        self.failUnlessEqual(result, [])

    def testFindFirstThree(self):
        result = [wibbrlib.cmp.first_by_kind(self.list, 3)]
        self.match(result, 3, "black")
        self.failUnlessEqual(result, [])

    def testFindFirstNone(self):
        result = wibbrlib.cmp.first_by_kind(self.list, 0)
        self.failUnlessEqual(result, None)

    def testFindAllStringOnes(self):
        result = wibbrlib.cmp.find_strings_by_kind(self.list, 1)
        self.failUnlessEqual(result, ["pink"])

    def testFindAllStringTwos(self):
        result = wibbrlib.cmp.find_strings_by_kind(self.list, 2)
        self.failUnlessEqual(result, ["pretty"])

    def testFindAllStringThrees(self):
        result = wibbrlib.cmp.find_strings_by_kind(self.list, 3)
        self.failUnlessEqual(result, ["black", "box"])

    def testFindAllStringNones(self):
        result = wibbrlib.cmp.find_strings_by_kind(self.list, 0)
        self.failUnlessEqual(result, [])

    def testFindFirstStringOne(self):
        result = wibbrlib.cmp.first_string_by_kind(self.list, 1)
        self.failUnlessEqual(result, "pink")

    def testFindFirstStringTwo(self):
        result = wibbrlib.cmp.first_string_by_kind(self.list, 2)
        self.failUnlessEqual(result, "pretty")

    def testFindFirstStringThree(self):
        result = wibbrlib.cmp.first_string_by_kind(self.list, 3)
        self.failUnlessEqual(result, "black")

    def testFindFirstStringNone(self):
        result = wibbrlib.cmp.first_string_by_kind(self.list, 0)
        self.failUnlessEqual(result, None)


class GetVarintVAlueTest(unittest.TestCase):

    def test(self):
        c = wibbrlib.cmp.create(1, wibbrlib.varint.encode(12765))
        self.failUnlessEqual(wibbrlib.cmp.get_varint_value(c), 12765)


class FindVarintTests(unittest.TestCase):

    def test(self):
        list = []
        for i in range(1024):
            encoded = wibbrlib.varint.encode(i)
            c = wibbrlib.cmp.create(i, encoded)
            list.append(c)

        for i in range(1024):
            self.failUnlessEqual(wibbrlib.cmp.first_varint_by_kind(list, i), 
                                 i)
