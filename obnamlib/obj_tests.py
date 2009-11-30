# Copyright (C) 2009  Lars Wirzenius
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


import unittest

import obnamlib


class TestObject(obnamlib.BackupObject):

    fields = (('foo', obnamlib.TYPE_STR), ('bar', obnamlib.TYPE_INT),
              ('foobar', obnamlib.TYPE_ID_LIST), ('baz', obnamlib.TYPE_ID))


class BackupObjectTests(unittest.TestCase):

    def setUp(self):
        self.obj = TestObject()

    def test_has_no_id(self):
        self.assertEqual(self.obj.id, None)

    def test_raises_exception_for_bad_attribute(self):
        self.assertRaises(AttributeError, getattr, self.obj, 'notexist')

    def test_raises_exception_for_setting_bad_attribute(self):
        self.assertRaises(Exception, setattr, self.obj, 'notexist', None)

    def test_has_no_foo(self):
        self.assertEqual(self.obj.foo, None)
        
    def test_sets_foo(self):
        self.obj.foo = 'yo'
        self.assertEqual(self.obj.foo, 'yo')
        
    def test_raises_exception_if_setting_foo_to_non_string(self):
        self.assertRaises(Exception, setattr, self.obj, 'foo', 0)
    
    def test_sets_foo_to_None(self):
        self.obj.foo = 'yo'
        self.obj.foo = None
        self.assertEqual(self.obj.foo, None)

    def test_has_no_bar(self):
        self.assertEqual(self.obj.bar, None)
        
    def test_sets_bar(self):
        self.obj.bar = 12765
        self.assertEqual(self.obj.bar, 12765)
        
    def test_raises_exception_if_setting_bar_to_non_int(self):
        self.assertRaises(Exception, setattr, self.obj, 'bar', 'yo')
    
    def test_sets_bar_to_None(self):
        self.obj.bar = 0
        self.obj.bar = None
        self.assertEqual(self.obj.bar, None)

    def test_has_no_foobar(self):
        self.assertEqual(self.obj.foobar, None)
        
    def test_sets_foobar(self):
        self.obj.foobar = [1, 2, 3]
        self.assertEqual(self.obj.foobar, [1, 2, 3])
        
    def test_raises_exception_if_setting_foobar_to_non_list(self):
        self.assertRaises(Exception, setattr, self.obj, 'foobar', 'yo')
        
    def test_raises_exception_if_setting_foobar_to_non_idlist(self):
        self.assertRaises(Exception, setattr, self.obj, 'foobar', ['yo'])
    
    def test_sets_foobar_to_None(self):
        self.obj.foobar = [1]
        self.obj.foobar = None
        self.assertEqual(self.obj.foobar, None)

    def test_has_no_baz(self):
        self.assertEqual(self.obj.baz, None)
        
    def test_sets_baz(self):
        self.obj.baz = 1
        self.assertEqual(self.obj.baz, 1)
        
    def test_raises_exception_if_setting_baz_to_non_id(self):
        self.assertRaises(Exception, setattr, self.obj, 'baz', 'yo')
        
    def test_sets_baz_to_None(self):
        self.obj.baz = 1
        self.obj.baz = None
        self.assertEqual(self.obj.baz, None)

    def test_sets_values_using_keyword_args_to_initializer(self):
        obj = TestObject(foo='foo', bar=12765, foobar=[1, 2, 3],
                         baz=4)
        self.assertEqual(obj.foo, 'foo')
        self.assertEqual(obj.bar, 12765)
        self.assertEqual(obj.foobar, [1, 2, 3])
        self.assertEqual(obj.baz, 4)


class TestMetadataObject(obnamlib.MetadataObject):

    fields = (('foo', obnamlib.TYPE_STR),)


class MetadataObjectTests(unittest.TestCase):

    def test_sets_mtime(self):
        obj = TestMetadataObject(st_mtime=123)
        self.assertEqual(obj.st_mtime, 123)

