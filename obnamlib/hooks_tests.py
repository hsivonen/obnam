# Copyright (C) 2009-2014  Lars Wirzenius
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

import base64

class HookTests(unittest.TestCase):

    def setUp(self):
        self.hook = obnamlib.Hook()

    def callback(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    def callback2(self, *args, **kwargs):
        self.args2 = args
        self.kwargs2 = kwargs

    def test_has_no_callbacks_by_default(self):
        self.assertEqual(self.hook.callbacks, [])

    def test_adds_callback(self):
        self.hook.add_callback(self.callback)
        self.assertEqual(self.hook.callbacks, [self.callback])

    def test_adds_callback_only_once(self):
        self.hook.add_callback(self.callback)
        self.hook.add_callback(self.callback)
        self.assertEqual(self.hook.callbacks, [self.callback])

    def test_adds_two_callbacks(self):
        id1 = self.hook.add_callback(self.callback)
        id2 = self.hook.add_callback(self.callback2,
                                     obnamlib.Hook.DEFAULT_PRIORITY + 1)
        self.assertEqual(self.hook.callbacks, [self.callback, self.callback2])
        self.assertNotEqual(id1, id2)

    def test_adds_callbacks_in_reverse_order(self):
        id1 = self.hook.add_callback(self.callback)
        id2 = self.hook.add_callback(self.callback2,
                                     obnamlib.Hook.DEFAULT_PRIORITY - 1)
        self.assertEqual(self.hook.callbacks, [self.callback2, self.callback])
        self.assertNotEqual(id1, id2)

    def test_calls_callback(self):
        self.hook.add_callback(self.callback)
        self.hook.call_callbacks('bar', kwarg='foobar')
        self.assertEqual(self.args, ('bar',))
        self.assertEqual(self.kwargs, { 'kwarg': 'foobar' })

    def test_removes_callback(self):
        cb_id = self.hook.add_callback(self.callback)
        self.hook.remove_callback(cb_id)
        self.assertEqual(self.hook.callbacks, [])

class NeverAddsFilter(object):

    def __init__(self):
        self.tag = "never"

    def filter_read(self, data, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.wasread = True
        return data

    def filter_write(self, data, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.wasread = False
        return data

class Base64Filter(object):

    def __init__(self):
        self.tag = "base64"

    def filter_read(self, data, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.wasread = True
        return base64.b64decode(data)

    def filter_write(self, data, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.wasread = False
        return base64.b64encode(data)

class FilterHookTests(unittest.TestCase):

    def setUp(self):
        self.hook = obnamlib.FilterHook()

    def test_add_filter_ok(self):
        self.hook.add_callback(NeverAddsFilter())

    def test_never_filter_no_tags(self):
        self.hook.add_callback(NeverAddsFilter())
        self.assertEquals(self.hook.run_filter_write("foo"), "\0foo")

    def test_never_filter_clean_revert(self):
        self.hook.add_callback(NeverAddsFilter())
        self.assertEquals(self.hook.run_filter_read("\0foo"), "foo")

    def test_base64_filter_encode(self):
        self.hook.add_callback(Base64Filter())
        self.assertEquals(self.hook.run_filter_write("OK"), "base64\0AE9L")

    def test_base64_filter_decode(self):
        self.hook.add_callback(Base64Filter())
        self.assertEquals(self.hook.run_filter_read("base64\0AE9L"), "OK")

    def test_no_tag_raises_error(self):
        with self.assertRaises(obnamlib.NoFilterTagError):
            self.hook.run_filter_read('no NUL bytes in this string')

    def test_missing_filter_raises(self):
        self.assertRaises(obnamlib.MissingFilterError,
                          self.hook.run_filter_read, "missing\0")

    def test_can_remove_filters(self):
        myfilter = NeverAddsFilter()
        filterid = self.hook.add_callback(myfilter)
        self.hook.remove_callback(filterid)
        self.assertEquals(self.hook.callbacks, [])

    def test_call_callbacks_raises(self):
        self.assertRaises(NotImplementedError, self.hook.call_callbacks, "")

class HookManagerTests(unittest.TestCase):

    def setUp(self):
        self.hooks = obnamlib.HookManager()
        self.hooks.new('foo')

    def callback(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    def test_has_no_tests_initially(self):
        hooks = obnamlib.HookManager()
        self.assertEqual(hooks.hooks, {})

    def test_adds_new_hook(self):
        self.assert_(self.hooks.hooks.has_key('foo'))

    def test_adds_new_filter_hook(self):
        self.hooks.new_filter('bar')
        self.assert_('bar' in self.hooks.filters)

    def test_adds_callback(self):
        self.hooks.add_callback('foo', self.callback)
        self.assertEqual(self.hooks.hooks['foo'].callbacks, [self.callback])

    def test_removes_callback(self):
        cb_id = self.hooks.add_callback('foo', self.callback)
        self.hooks.remove_callback('foo', cb_id)
        self.assertEqual(self.hooks.hooks['foo'].callbacks, [])

    def test_calls_callbacks(self):
        self.hooks.add_callback('foo', self.callback)
        self.hooks.call('foo', 'bar', kwarg='foobar')
        self.assertEqual(self.args, ('bar',))
        self.assertEqual(self.kwargs, { 'kwarg': 'foobar' })

    def test_filter_write_returns_value_of_callbacks(self):
        self.hooks.new_filter('bar')
        self.assertEquals(self.hooks.filter_write('bar', "foo"), "\0foo")

    def test_filter_read_returns_value_of_callbacks(self):
        self.hooks.new_filter('bar')
        self.assertEquals(self.hooks.filter_read('bar', "\0foo"), "foo")

    def test_add_callbacks_to_filters(self):
        self.hooks.new_filter('bar')
        filt = NeverAddsFilter()
        self.hooks.add_callback('bar', filt)
        self.assertEquals(self.hooks.filters['bar'].callbacks, [filt])

    def test_remove_callbacks_from_filters(self):
        self.hooks.new_filter('bar')
        filt = NeverAddsFilter()
        self.hooks.add_callback('bar', filt)
        self.hooks.remove_callback('bar', filt)
        self.assertEquals(self.hooks.filters['bar'].callbacks, [])
