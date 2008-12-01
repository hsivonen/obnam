# Copyright (C) 2008  Lars Wirzenius <liw@liw.fi>
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


import unittest

import obnamlib


class KindsTests(unittest.TestCase):

    def testIsEmptyInitially(self):
        kinds = obnamlib.Kinds()
        self.assertEqual(kinds.pairs(), [])

    def testAddsOneKindCorrectl(self):
        kinds = obnamlib.Kinds()
        kinds.add(1, "foo")
        self.assertEqual(kinds.pairs(), [(1, "foo")])

    def testAddsMappingInBothDirections(self):
        kinds = obnamlib.Kinds()
        kinds.add(1, "foo")
        self.assertEqual(kinds.nameof(1), "foo")
        self.assertEqual(kinds.codeof("foo"), 1)

    def testRaisesErrorForUnknownCode(self):
        kinds = obnamlib.Kinds()
        self.assertRaises(KeyError, kinds.nameof, 1)

    def testRaisesErrorForUnknownName(self):
        kinds = obnamlib.Kinds()
        self.assertRaises(KeyError, kinds.codeof, "foo")
