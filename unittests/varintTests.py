"""Unit tests for wibbrlib.varint."""


import unittest


import wibbrlib.varint


class VarintEncodeDecodeTests(unittest.TestCase):

    def test(self):
        numbers = (0, 1, 127, 128, 0xff00)
        for i in numbers:
            str = wibbrlib.varint.encode(i)
            (i2, pos) = wibbrlib.varint.decode(str, 0)
            self.failUnlessEqual(i, i2)
            self.failUnlessEqual(pos, len(str))
