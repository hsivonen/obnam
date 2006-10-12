"""Unit tests for wibbrlib.varint."""


import unittest


import wibbrlib.varint


class VarintEncoding(unittest.TestCase):

    def testZero(self):
        self.failUnlessEqual(wibbrlib.varint.encode(0), "\0")

    def testNegative(self):
        self.failUnlessRaises(AssertionError, wibbrlib.varint.encode, -1)

    def testSmallPositives(self):
        self.failUnlessEqual(wibbrlib.varint.encode(1), "\1")
        self.failUnlessEqual(wibbrlib.varint.encode(127), "\177")

    def test128(self):
        self.failUnlessEqual(wibbrlib.varint.encode(128), "\x81\0")

    def testBigPositive(self):
        self.failUnlessEqual(wibbrlib.varint.encode(0xff00),
                             "\203\376\0")


class VarintDecodeTests(unittest.TestCase):

    def testZero(self):
        self.failUnlessEqual(wibbrlib.varint.decode("\0", 0), (0, 1))

    def testSmall(self):
        self.failUnlessEqual(wibbrlib.varint.decode("\1", 0), (1, 1))
        self.failUnlessEqual(wibbrlib.varint.decode("\177", 0), (127, 1))

    def test128(self):
        self.failUnlessEqual(wibbrlib.varint.decode("\x81\0", 0), (128, 2))

    def testBigPositive(self):
        self.failUnlessEqual(wibbrlib.varint.decode("\203\376\0", 0), 
                             (0xff00, 3))


class VarintEncodeDecodeTests(unittest.TestCase):

    def test(self):
        numbers = (0, 1, 127, 128, 0xff00)
        for i in numbers:
            str = wibbrlib.varint.encode(i)
            (i2, pos) = wibbrlib.varint.decode(str, 0)
            self.failUnlessEqual(i, i2)
            self.failUnlessEqual(pos, len(str))
