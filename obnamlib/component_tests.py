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

    def setUp(self):
        self.scmp = obnamlib.Component(obnamlib.FILENAME)
        self.ccmp = obnamlib.Component(obnamlib.OBJECT)

    def testSetsKindCorrectly(self):
        self.assertEqual(self.scmp.kind, obnamlib.FILENAME)

    def testInitiallySetsValueToEmptyString(self):
        self.assertEqual(self.scmp.string, "")

    def testSetsStringValueCorrectly(self):
        self.scmp.string = "foo"
        self.assertEqual(self.scmp.string, "foo")

    def testRefusesToAccessStringForCompositeComponent(self):
        self.assertRaises(obnamlib.Exception, lambda: self.ccmp.string)

    def testRefusesToSetStringForCompositeComponent(self):
        def set():
            self.ccmp.string = "foo"
        self.assertRaises(obnamlib.Exception, set)

    def testInitiallyCreatesNoChildren(self):
        self.assertEqual(self.ccmp.children, [])

    def testSetsChildrenCorrectly(self):
        self.ccmp.children = [self.scmp]
        self.assertEqual(self.ccmp.children, [self.scmp])

    def testAddsChildCorrectly(self):
        self.ccmp.children.append(self.scmp)
        self.assertEqual(self.ccmp.children, [self.scmp])

    def testAddsSecondChildCorrectly(self):
        a = obnamlib.Component(obnamlib.FILENAME)
        b = obnamlib.Component(obnamlib.FILENAME)
        self.ccmp.children.append(a)
        self.ccmp.children.append(b)
        self.assertEqual(self.ccmp.children, [a, b])

    def testRefusesToAccessChildrenForNonCompositeComponent(self):
        self.assertRaises(obnamlib.Exception, lambda: self.scmp.children)
