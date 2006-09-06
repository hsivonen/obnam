"""Unit tests for wibbrlib."""


import unittest


from wibbrlib import *


class VarintEncoding(unittest.TestCase):

    def testZero(self):
        self.failUnlessEqual(varint_encode(0), "\0")

    def testNegative(self):
        self.failUnlessRaises(AssertionError, varint_encode, -1)

    def testSmallPositives(self):
        self.failUnlessEqual(varint_encode(1), "\1")
        self.failUnlessEqual(varint_encode(127), "\177")

    def test128(self):
        self.failUnlessEqual(varint_encode(128), "\x81\0")

    def testBigPositive(self):
        self.failUnlessEqual(varint_encode(0xff00),
                             "\203\376\0")


class VarintDecodeTests(unittest.TestCase):

    def testZero(self):
        self.failUnlessEqual(varint_decode("\0", 0), (0, 1))

    def testSmall(self):
        self.failUnlessEqual(varint_decode("\1", 0), (1, 1))
        self.failUnlessEqual(varint_decode("\177", 0), (127, 1))

    def test128(self):
        self.failUnlessEqual(varint_decode("\x81\0", 0), (128, 2))

    def testBigPositive(self):
        self.failUnlessEqual(varint_decode("\203\376\0", 0), 
                             (0xff00, 3))


class VarintEncodeDecodeTests(unittest.TestCase):

    def test(self):
        numbers = (0, 1, 127, 128, 0xff00)
        for i in numbers:
            str = varint_encode(i)
            (i2, pos) = varint_decode(str, 0)
            self.failUnlessEqual(i, i2)
            self.failUnlessEqual(pos, len(str))


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


class ObjectEncodingTests(unittest.TestCase):

    def testEmptyObject(self):
        self.failUnlessEqual(object_encode("uuid", 33, []),
                             "\4\1uuid\1\2\41")

    def testNonEmptyObject(self):
        self.failUnlessEqual(object_encode("uuid", 33, ["\1\77x"]),
                             "\4\1uuid\1\2\41\1\77x")


class ObjectEncodingDecodingTests(unittest.TestCase):

    def test(self):
        component1 = component_encode(0xdeadbeef, "hello")
        component2 = component_encode(0xcafebabe, "world")
        object = object_encode("uuid", 0xdada, [component1, component2])
        self.failIfEqual(object, None)
        self.failIfEqual(object, "")
        
        components = object_decode(object, 0)
        self.failUnlessEqual(len(components), 4) # id, type, cmpnt1, cmpnt2
        
        self.failUnlessEqual(components[0], (OBJID, "uuid"))
        self.failUnlessEqual(components[1], (OBJTYPE, 0xdada))
        self.failUnlessEqual(components[2], (0xdeadbeef, "hello"))
        self.failUnlessEqual(components[3], (0xcafebabe, "world"))


class ObjectQueueTests(unittest.TestCase):

    def testCreate(self):
        self.failUnlessEqual(object_queue_create(), [])

    def testAdd(self):
        oq = object_queue_create()
        object_queue_add(oq, "abc")
        self.failUnlessEqual(oq, ["abc"])

    def testSize(self):
        oq = object_queue_create()
        self.failUnlessEqual(object_queue_combined_size(oq), 0)
        object_queue_add(oq, "abc")
        self.failUnlessEqual(object_queue_combined_size(oq), 3)
        object_queue_add(oq, "abc")
        self.failUnlessEqual(object_queue_combined_size(oq), 6)


if __name__ == "__main__":
    unittest.main()
