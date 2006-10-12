"""Unit tests for wibbrlib.component."""


import os
import unittest


import wibbrlib


class ComponentTypeNameTests(unittest.TestCase):

    def test(self):
        t = wibbrlib.component.component_type_name
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
        self.failUnlessEqual(c.subcomponents, [])

    def testCreateComposite(self):
        leaf1 = wibbrlib.component.create(1, "pink")
        leaf2 = wibbrlib.component.create(2, "pretty")
        c = wibbrlib.component.create(3, [leaf1, leaf2])
        self.failUnlessEqual(wibbrlib.component.get_type(c), 3)
        self.failUnlessEqual(c.str, None)
        self.failUnlessEqual(wibbrlib.component.get_subcomponents(c), 
                             [leaf1, leaf2])


class ComponentEncodingDecodingTests(unittest.TestCase):

    def doit(self, type, data):
        str = wibbrlib.component.component_encode(type, data)
        (type2, data2, pos) = wibbrlib.component.component_decode(str, 0)
        self.failUnlessEqual(type, type2)
        self.failUnlessEqual(data, data2)
        self.failUnlessEqual(pos, len(str))

    def testEmpty(self):
        self.doit(1, "")

    def testNonempty(self):
        self.doit(2, "hello, world\0this is fun")


class ComponentDecodeAllTests(unittest.TestCase):

    def testDecodeAll(self):
        c1 = wibbrlib.component.component_encode(1, "pink")
        c2 = wibbrlib.component.component_encode(2, "pretty")
        c = c1 + c2
        list = wibbrlib.component.component_decode_all(c, 0)
        self.failUnlessEqual(list, [(1, "pink"), (2, "pretty")])
