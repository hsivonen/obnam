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


class ComponentTests(unittest.TestCase):

    def testSetsKindCorrectly(self):
        cmp = obnamlib.Component(42)
        self.assertEqual(cmp.kind, 42)

    def testInitiallyEmptyString(self):
        cmp = obnamlib.Component(obnamlib.FILENAME)
        self.assertEqual(cmp.string, "")

    def testSetsStringValueCorrectly(self):
        cmp = obnamlib.Component(obnamlib.FILENAME)
        cmp.string = "foo"
        self.assertEqual(cmp.string, "foo")

    def testRefusesToAccessStringForCompositeComponent(self):
        cmp = obnamlib.Component(obnamlib.OBJECT)
        self.assertRaises(obnamlib.Exception, lambda: cmp.string)

    def testRefusesToSetStringForCompositeComponent(self):
        cmp = obnamlib.Component(obnamlib.OBJECT)
        def set():
            cmp.string = "foo"
        self.assertRaises(obnamlib.Exception, set)
