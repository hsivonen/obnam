"""Unit tests for wibbrlib.component."""


import os
import unittest


from wibbrlib.component import *
import wibbrlib


class ComponentTypeNameTests(unittest.TestCase):

    def test(self):
        c = component_type_name
        self.failUnlessEqual(c(-12765), "CMP_UNKNOWN")
        self.failUnlessEqual(c(CMP_OBJID), "CMP_OBJID")
        self.failUnlessEqual(c(CMP_OBJTYPE), "CMP_OBJTYPE")
        self.failUnlessEqual(c(CMP_BLKID), "CMP_BLKID")
        self.failUnlessEqual(c(CMP_FILECHUNK), "CMP_FILECHUNK")
        self.failUnlessEqual(c(CMP_OBJPART), "CMP_OBJPART")
        self.failUnlessEqual(c(CMP_OBJMAP), "CMP_OBJMAP")
        self.failUnlessEqual(c(CMP_ST_MODE), "CMP_ST_MODE")
        self.failUnlessEqual(c(CMP_ST_INO), "CMP_ST_INO")
        self.failUnlessEqual(c(CMP_ST_DEV), "CMP_ST_DEV")
        self.failUnlessEqual(c(CMP_ST_NLINK), "CMP_ST_NLINK")
        self.failUnlessEqual(c(CMP_ST_UID), "CMP_ST_UID")
        self.failUnlessEqual(c(CMP_ST_GID), "CMP_ST_GID")
        self.failUnlessEqual(c(CMP_ST_SIZE), "CMP_ST_SIZE")
        self.failUnlessEqual(c(CMP_ST_ATIME), "CMP_ST_ATIME")
        self.failUnlessEqual(c(CMP_ST_MTIME), "CMP_ST_MTIME")
        self.failUnlessEqual(c(CMP_ST_CTIME), "CMP_ST_CTIME")
        self.failUnlessEqual(c(CMP_ST_BLOCKS), "CMP_ST_BLOCKS")
        self.failUnlessEqual(c(CMP_ST_BLKSIZE), "CMP_ST_BLKSIZE")
        self.failUnlessEqual(c(CMP_ST_RDEV), "CMP_ST_RDEV")
        self.failUnlessEqual(c(CMP_CONTREF), "CMP_CONTREF")
        self.failUnlessEqual(c(CMP_NAMEIPAIR), "CMP_NAMEIPAIR")
        self.failUnlessEqual(c(CMP_INODEREF), "CMP_INODEREF")
        self.failUnlessEqual(c(CMP_FILENAME), "CMP_FILENAME")
        self.failUnlessEqual(c(CMP_SIGDATA), "CMP_SIGDATA")
        self.failUnlessEqual(c(CMP_SIGREF), "CMP_SIGREF")
        self.failUnlessEqual(c(CMP_GENREF), "CMP_GENREF")
        self.failUnlessEqual(c(CMP_GENLIST), "CMP_GENLIST")
        self.failUnlessEqual(c(CMP_OBJREF), "CMP_OBJREF")
        self.failUnlessEqual(c(CMP_BLOCKREF), "CMP_BLOCKREF")
        self.failUnlessEqual(c(CMP_MAPREF), "CMP_MAPREF")
        self.failUnlessEqual(c(CMP_FILEPARTREF), "CMP_FILEPARTREF")


class CreateComponentTests(unittest.TestCase):

    def testCreateLeaf(self):
        c = wibbrlib.component.create_leaf(1, "pink")
        self.failIfEqual(c, None)


class ComponentEncodingDecodingTests(unittest.TestCase):

    def doit(self, type, data):
        str = component_encode(type, data)
        (type2, data2, pos) = component_decode(str, 0)
        self.failUnlessEqual(type, type2)
        self.failUnlessEqual(data, data2)
        self.failUnlessEqual(pos, len(str))

    def testEmpty(self):
        self.doit(1, "")

    def testNonempty(self):
        self.doit(2, "hello, world\0this is fun")


class ComponentDecodeAllTests(unittest.TestCase):

    def testDecodeAll(self):
        c1 = component_encode(1, "pink")
        c2 = component_encode(2, "pretty")
        c = c1 + c2
        list = component_decode_all(c, 0)
        self.failUnlessEqual(list, [(1, "pink"), (2, "pretty")])
