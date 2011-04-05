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


class HookTests(unittest.TestCase):

    def setUp(self):
        self.hook = obnamlib.Hook()
        
    def callback(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    def test_has_no_callbacks_by_default(self):
        self.assertEqual(self.hook.callbacks, [])
        
    def test_adds_callback(self):
        self.hook.add_callback(self.callback)
        self.assertEqual(self.hook.callbacks, [self.callback])
        
    def test_adds_callback_only_once(self):
        self.hook.add_callback(self.callback)
        self.hook.add_callback(self.callback)
        self.assertEqual(self.hook.callbacks, [self.callback])

    def test_calls_callback(self):
        self.hook.add_callback(self.callback)
        self.hook.call_callbacks('bar', kwarg='foobar')
        self.assertEqual(self.args, ('bar',))
        self.assertEqual(self.kwargs, { 'kwarg': 'foobar' })

    def test_removes_callback(self):
        cb_id = self.hook.add_callback(self.callback)
        self.hook.remove_callback(cb_id)
        self.assertEqual(self.hook.callbacks, [])


class FilterHookTests(unittest.TestCase):

    def setUp(self):
        self.hook = obnamlib.FilterHook()

    def callback(self, data):
        return data + ['callback']

    def test_returns_argument_if_no_callbacks(self):
        self.assertEqual(self.hook.call_callbacks(['foo']), ['foo'])
        
    def test_calls_callback_and_returns_modified_data(self):
        self.hook.add_callback(self.callback)
        data = self.hook.call_callbacks([])
        self.assertEqual(data, ['callback'])

        
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
        self.assert_('bar' in self.hooks.hooks)
        
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

    def test_call_returns_value_of_callbacks(self):
        self.hooks.new_filter('bar')
        self.hooks.add_callback('bar', lambda data: data + 1)
        self.assertEqual(self.hooks.call('bar', 1), 2)

