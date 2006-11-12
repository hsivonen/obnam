"""Unit tests for obnam.varint."""


import unittest


import obnam.varint


class VarintEncodeDecodeTests(unittest.TestCase):

    def test(self):
        numbers = (0, 1, 127, 128, 0xff00)
        for i in numbers:
            str = obnam.varint.encode(i)
            (i2, pos) = obnam.varint.decode(str, 0)
            self.failUnlessEqual(i, i2)
            self.failUnlessEqual(pos, len(str))
