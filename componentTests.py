"""Unit tests for wibbrlib.component."""


import os
import unittest


import wibbrlib


class ComponentTypeNameTests(unittest.TestCase):

    def test(self):
        t = wibbrlib.component.type_name
        c = wibbrlib.component
        self.failUnlessEqual(t(-12765), "CMP_UNKNOWN")
        self.failUnlessEqual(t(c.CMP_OBJID), "CMP_OBJID")
        self.failUnlessEqual(t(c.CMP_OBJTYPE), "CMP_OBJTYPE")
        self.failUnlessEqual(t(c.CMP_BLKID), "CMP_BLKID")
        self.failUnlessEqual(t(c.CMP_FILECHUNK), "CMP_FILECHUNK")
        self.failUnlessEqual(t(c.CMP_OBJPART), "CMP_OBJPART")
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
        self.failUnlessEqual(t(c.CMP_GENLIST), "CMP_GENLIST")
        self.failUnlessEqual(t(c.CMP_OBJREF), "CMP_OBJREF")
        self.failUnlessEqual(t(c.CMP_BLOCKREF), "CMP_BLOCKREF")
        self.failUnlessEqual(t(c.CMP_MAPREF), "CMP_MAPREF")
        self.failUnlessEqual(t(c.CMP_FILEPARTREF), "CMP_FILEPARTREF")


class CreateComponentTests(unittest.TestCase):

    def testCreateLeaf(self):
        c = wibbrlib.component.create(1, "pink")
        self.failIfEqual(c, None)
        self.failUnlessEqual(wibbrlib.component.get_type(c), 1)
        self.failUnlessEqual(wibbrlib.component.get_string_value(c), "pink")
        self.failUnlessEqual(wibbrlib.component.is_composite(c), False)

    def testCreateComposite(self):
        leaf1 = wibbrlib.component.create(1, "pink")
        leaf2 = wibbrlib.component.create(2, "pretty")
        c = wibbrlib.component.create(3, [leaf1, leaf2])
        self.failUnlessEqual(wibbrlib.component.get_type(c), 3)
        self.failUnlessEqual(wibbrlib.component.is_composite(c), True)
        self.failUnlessEqual(wibbrlib.component.get_subcomponents(c), 
                             [leaf1, leaf2])


class ComponentEncodingDecodingTests(unittest.TestCase):

    def doit(self, c_type, data):
        c = wibbrlib.component.create(c_type, data)
        encoded = wibbrlib.component.encode(c)
        (c2, pos) = wibbrlib.component.decode(encoded, 0)
        encoded2 = wibbrlib.component.encode(c2)
        self.failUnlessEqual(encoded, encoded2)
        self.failUnlessEqual(wibbrlib.component.get_type(c), 
                             wibbrlib.component.get_type(c2))
        self.failUnlessEqual(wibbrlib.component.is_composite(c), 
                             wibbrlib.component.is_composite(c2))
        self.failUnlessEqual(wibbrlib.component.is_composite(c),
                             type(data) == type([]))
        if not wibbrlib.component.is_composite(c):
            self.failUnlessEqual(wibbrlib.component.get_string_value(c),
                                 wibbrlib.component.get_string_value(c2))            
        self.failUnlessEqual(pos, len(encoded))

    def testEmpty(self):
        self.doit(1, "")

    def testNonempty(self):
        self.doit(2, "hello, world\0this is fun")

    def testEmptyComposite(self):
        self.doit(wibbrlib.component.CMP_OBJPART, [])

    def testNonemptyComposite(self):
        c1 = wibbrlib.component.create(1, "pink")
        c2 = wibbrlib.component.create(2, "pretty")
        self.doit(wibbrlib.component.CMP_OBJPART, [c1, c2])


class ComponentDecodeAllTests(unittest.TestCase):

    def remove_component(self, list, type, value):
        self.failUnlessEqual(wibbrlib.component.get_type(list[0]), type)
        self.failUnlessEqual(wibbrlib.component.get_string_value(list[0]), 
                             value)
        del list[0]

    def testDecodeAll(self):
        c1 = wibbrlib.component.create(1, "pink")
        c2 = wibbrlib.component.create(2, "pretty")
        e1 = wibbrlib.component.encode(c1)
        e2 = wibbrlib.component.encode(c2)
        e = e1 + e2
        list = wibbrlib.component.decode_all(e, 0)
        self.remove_component(list, 1, "pink")
        self.remove_component(list, 2, "pretty")
        self.failUnlessEqual(list, [])


class FindTests(unittest.TestCase):

    def setUp(self):
        self.list = [(1, "pink"), (2, "pretty"), (3, "black"), (3, "box")]
        self.list = [wibbrlib.component.create(a, b) for a, b in self.list]

    def tearDown(self):
        del self.list

    def match(self, result, type, value):
        self.failUnless(len(result) > 0)
        c = result[0]
        self.failUnlessEqual(wibbrlib.component.get_type(c), type)
        self.failUnlessEqual(wibbrlib.component.get_string_value(c), value)
        del result[0]

    def testFindAllOnes(self):
        result = wibbrlib.component.find_by_type(self.list, 1)
        self.match(result, 1, "pink")
        self.failUnlessEqual(result, [])

    def testFindAllTwos(self):
        result = wibbrlib.component.find_by_type(self.list, 2)
        self.match(result, 2, "pretty")
        self.failUnlessEqual(result, [])

    def testFindAllThrees(self):
        result = wibbrlib.component.find_by_type(self.list, 3)
        self.match(result, 3, "black")
        self.match(result, 3, "box")
        self.failUnlessEqual(result, [])

    def testFindAllNones(self):
        result = wibbrlib.component.find_by_type(self.list, 0)
        self.failUnlessEqual(result, [])

    def testFindFirstOne(self):
        result = [wibbrlib.component.first_by_type(self.list, 1)]
        self.match(result, 1, "pink")
        self.failUnlessEqual(result, [])

    def testFindFirstTwo(self):
        result = [wibbrlib.component.first_by_type(self.list, 2)]
        self.match(result, 2, "pretty")
        self.failUnlessEqual(result, [])

    def testFindFirstThree(self):
        result = [wibbrlib.component.first_by_type(self.list, 3)]
        self.match(result, 3, "black")
        self.failUnlessEqual(result, [])

    def testFindFirstNone(self):
        result = wibbrlib.component.first_by_type(self.list, 0)
        self.failUnlessEqual(result, None)

    def testFindAllStringOnes(self):
        result = wibbrlib.component.find_strings_by_type(self.list, 1)
        self.failUnlessEqual(result, ["pink"])

    def testFindAllStringTwos(self):
        result = wibbrlib.component.find_strings_by_type(self.list, 2)
        self.failUnlessEqual(result, ["pretty"])

    def testFindAllStringThrees(self):
        result = wibbrlib.component.find_strings_by_type(self.list, 3)
        self.failUnlessEqual(result, ["black", "box"])

    def testFindAllStringNones(self):
        result = wibbrlib.component.find_strings_by_type(self.list, 0)
        self.failUnlessEqual(result, [])

    def testFindFirstStringOne(self):
        result = wibbrlib.component.first_string_by_type(self.list, 1)
        self.failUnlessEqual(result, "pink")

    def testFindFirstStringTwo(self):
        result = wibbrlib.component.first_string_by_type(self.list, 2)
        self.failUnlessEqual(result, "pretty")

    def testFindFirstStringThree(self):
        result = wibbrlib.component.first_string_by_type(self.list, 3)
        self.failUnlessEqual(result, "black")

    def testFindFirstStringNone(self):
        result = wibbrlib.component.first_string_by_type(self.list, 0)
        self.failUnlessEqual(result, None)
