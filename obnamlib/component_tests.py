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
        self.scmp = obnamlib.Component(kind=obnamlib.OBJID)
        self.ccmp = obnamlib.Component(kind=obnamlib.FILE)

    def test_sets_kind_correctly(self):
        self.assertEqual(self.scmp.kind, obnamlib.OBJID)
        self.assertEqual(self.ccmp.kind, obnamlib.FILE)

    def test_initially_sets_value_to_empty_string(self):
        self.assertEqual(self.scmp.string, "")

    def test_sets_string_value_correctly(self):
        self.scmp.string = "foo"
        self.assertEqual(self.scmp.string, "foo")

    def test_sets_string_value_via_initializer_correctly(self):
        c = obnamlib.Component(kind=obnamlib.OBJID, string="foo")
        self.assertEqual(c.string, "foo")

    def test_refuses_to_set_string_value_to_non_string_value(self):
        self.assertRaises(obnamlib.Exception, self.scmp.set_string, None)

    def test_refuses_to_access_string_for_composite_component(self):
        self.assertRaises(obnamlib.Exception, lambda: self.ccmp.string)

    def test_refuses_to_set_string_for_composite_component(self):
        def set():
            self.ccmp.string = "foo"
        self.assertRaises(obnamlib.Exception, set)

    def test_initially_creates_no_children(self):
        self.assertEqual(self.ccmp.children, [])

    def test_sets_children_correctly(self):
        self.ccmp.children = [self.scmp]
        self.assertEqual(self.ccmp.children, [self.scmp])

    def test_sets_children_via_initializer_correctly(self):
        c = obnamlib.Component(kind=obnamlib.FILE, children=[self.scmp])
        self.assertEqual(c.children, [self.scmp])

    def test_adds_child_correctly(self):
        self.ccmp.children.append(self.scmp)
        self.assertEqual(self.ccmp.children, [self.scmp])

    def test_adds_second_child_correctly(self):
        a = obnamlib.Component(obnamlib.FILENAME)
        b = obnamlib.Component(obnamlib.FILENAME)
        self.ccmp.children.append(a)
        self.ccmp.children.append(b)
        self.assertEqual(self.ccmp.children, [a, b])

    def test_refuses_to_access_children_for_non_composite_component(self):
        self.assertRaises(obnamlib.Exception, lambda: self.scmp.children)


class CompositeTests(unittest.TestCase):

    def setUp(self):
        self.cmp = obnamlib.Component(kind=obnamlib.FILE)
        self.foo = obnamlib.Component(kind=obnamlib.OBJID, string="foo")
        self.foo2 = obnamlib.Component(kind=obnamlib.OBJID, string="foo2")
        self.bar = obnamlib.Component(kind=obnamlib.FILENAME, string="bar")
        self.cmp.children.append(self.foo)
        self.cmp.children.append(self.bar)
        self.cmp.children.append(self.foo2)

    def test_finds_by_kind(self):
        self.assertEqual(self.cmp.find(kind=obnamlib.OBJID), 
                         [self.foo, self.foo2])

    def test_finds_strings_by_kind(self):
        self.assertEqual(self.cmp.find_strings(kind=obnamlib.OBJID), 
                         ["foo", "foo2"])

    def test_finds_first_by_kind(self):
        self.assertEqual(self.cmp.first(kind=obnamlib.OBJID), self.foo)

    def test_first_returns_None_if_not_found(self):
        self.assertEqual(self.cmp.first(kind=obnamlib.BLKID), None)

    def test_finds_first_string_by_kind(self):
        self.assertEqual(self.cmp.first_string(kind=obnamlib.OBJID), "foo")

    def test_first_string_returns_None_if_not_found(self):
        self.assertEqual(self.cmp.first_string(kind=obnamlib.BLKID), None)

    def test_extract_finds_by_kind(self):
        self.assertEqual(self.cmp.extract(kind=obnamlib.OBJID), 
                         [self.foo, self.foo2])

    def test_extract_removes_matches(self):
        self.cmp.extract(kind=obnamlib.OBJID)
        self.assertEqual(self.cmp.children, [self.bar])


class StringComponentTests(unittest.TestCase):

    def test_sets_string_correctly(self):
        sc = obnamlib.StringComponent(kind=obnamlib.OBJID, string="foo")
        self.assertEqual(sc.string, "foo")
