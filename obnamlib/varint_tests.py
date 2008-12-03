# Copyright (C) 2006  Lars Wirzenius <liw@iki.fi>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.


"""Unit tests for obnamlib.varint."""


import unittest


import obnamlib


class VarintEncodeDecodeTests(unittest.TestCase):

    def test(self):
        numbers = (0, 1, 127, 128, 0xff00)
        for i in numbers:
            str = obnamlib.varint.encode(i)
            (i2, pos) = obnamlib.varint.decode(str, 0)
            self.failUnlessEqual(i, i2)
            self.failUnlessEqual(pos, len(str))

    def test_error(self):
        str = "asdf"
        n, pos = obnamlib.varint.decode(str, 0)
        self.failUnlessEqual(n, -1)
        self.failUnlessEqual(pos, 0)
        
    def test_many_encode_decode(self):
        numbers = [0, 1, 127, 128, 0xff00]
        encoded = obnamlib.varint.encode_many(numbers)
        decoded = obnamlib.varint.decode_many(encoded)
        self.assertEqual(numbers, decoded)
