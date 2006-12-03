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
        self.failUnlessEqual(t(c.ST_MODE), "ST_MODE")
        self.failUnlessEqual(t(c.ST_INO), "ST_INO")
        self.failUnlessEqual(t(c.ST_DEV), "ST_DEV")
        self.failUnlessEqual(t(c.ST_NLINK), "ST_NLINK")
        self.failUnlessEqual(t(c.ST_UID), "ST_UID")
        self.failUnlessEqual(t(c.ST_GID), "ST_GID")
        self.failUnlessEqual(t(c.ST_SIZE), "ST_SIZE")
        self.failUnlessEqual(t(c.ST_ATIME), "ST_ATIME")
        self.failUnlessEqual(t(c.ST_MTIME), "ST_MTIME")
        self.failUnlessEqual(t(c.ST_CTIME), "ST_CTIME")
        self.failUnlessEqual(t(c.ST_BLOCKS), "ST_BLOCKS")
        self.failUnlessEqual(t(c.ST_BLKSIZE), "ST_BLKSIZE")
        self.failUnlessEqual(t(c.ST_RDEV), "ST_RDEV")
        self.failUnlessEqual(t(c.CONTREF), "CONTREF")
        self.failUnlessEqual(t(c.NAMEIPAIR), "NAMEIPAIR")
        self.failUnlessEqual(t(c.INODEREF), "INODEREF")
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
        self.failUnlessEqual(obnam.cmp.get_kind(c), 1)
        self.failUnlessEqual(obnam.cmp.get_string_value(c), "pink")
        self.failUnlessEqual(obnam.cmp.is_composite(c), False)

    def testCreateComposite(self):
        leaf1 = obnam.cmp.create(1, "pink")
        leaf2 = obnam.cmp.create(2, "pretty")
        c = obnam.cmp.create(3, [leaf1, leaf2])
        self.failUnlessEqual(obnam.cmp.get_kind(c), 3)
        self.failUnlessEqual(obnam.cmp.is_composite(c), True)
        self.failUnlessEqual(obnam.cmp.get_subcomponents(c), 
                             [leaf1, leaf2])


class ComponentEncodingDecodingTests(unittest.TestCase):

    def doit(self, c_kind, data):
        c = obnam.cmp.create(c_kind, data)
        encoded = obnam.cmp.encode(c)
        (c2, pos) = obnam.cmp.decode(encoded, 0)
        encoded2 = obnam.cmp.encode(c2)
        self.failUnlessEqual(encoded, encoded2)
        self.failUnlessEqual(obnam.cmp.get_kind(c), 
                             obnam.cmp.get_kind(c2))
        self.failUnlessEqual(obnam.cmp.is_composite(c), 
                             obnam.cmp.is_composite(c2))
        self.failUnlessEqual(obnam.cmp.is_composite(c),
                             type(data) == type([]))
        if not obnam.cmp.is_composite(c):
            self.failUnlessEqual(obnam.cmp.get_string_value(c),
                                 obnam.cmp.get_string_value(c2))            
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
        self.failUnlessEqual(obnam.cmp.get_kind(list[0]), kind)
        self.failUnlessEqual(obnam.cmp.get_string_value(list[0]), 
                             value)
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
        self.failUnlessEqual(obnam.cmp.get_kind(c), kind)
        self.failUnlessEqual(obnam.cmp.get_string_value(c), value)
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
        self.failUnlessEqual(obnam.cmp.get_varint_value(c), 12765)


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
