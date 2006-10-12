"""Unit tests for wibbrlib.varint."""


import unittest


from wibbrlib.varint import *


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
