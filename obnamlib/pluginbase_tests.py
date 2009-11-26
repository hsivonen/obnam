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


class FakeApp(object):

    def __init__(self):
        self.hooks = self
        
    def add_callback(self, name, callback):
        return 'callback_id'
        
    def remove_callback(self, name, callback_id):
        self.removed = callback_id


class ObnamPluginTests(unittest.TestCase):

    def setUp(self):
        self.fakeapp = FakeApp()
        self.plugin = obnamlib.ObnamPlugin(self.fakeapp)

    def test_has_no_callbacks(self):
        self.assertEqual(self.plugin.callback_ids, [])
        
    def test_adds_callback(self):
        self.plugin.add_callback('foo', 'fake_callback')
        self.assertEqual(self.plugin.callback_ids, [('foo', 'callback_id')])
    
    def test_disable_wrapper_disables_callbacks(self):
        self.plugin.add_callback('foo', 'fake_callback')
        self.plugin.disable_wrapper()
        self.assertEqual(self.plugin.callback_ids, [])
        self.assertEqual(self.fakeapp.removed, 'callback_id')

    def test_enable_wrapper_works(self):
        self.plugin.enable_wrapper()

