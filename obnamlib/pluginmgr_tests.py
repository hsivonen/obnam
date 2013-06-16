# Copyright (C) 2009  Lars Wirzenius <liw@liw.fi>
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

from pluginmgr import Plugin, PluginManager


class PluginTests(unittest.TestCase):

    def setUp(self):
        self.plugin = Plugin()

    def test_name_is_class_name(self):
        self.assertEqual(self.plugin.name, 'Plugin')

    def test_description_is_empty_string(self):
        self.assertEqual(self.plugin.description, '')

    def test_version_is_zeroes(self):
        self.assertEqual(self.plugin.version, '0.0.0')

    def test_required_application_version_is_zeroes(self):
        self.assertEqual(self.plugin.required_application_version, '0.0.0')

    def test_enable_raises_exception(self):
        self.assertRaises(Exception, self.plugin.enable)

    def test_disable_raises_exception(self):
        self.assertRaises(Exception, self.plugin.disable)

    def test_enable_wrapper_calls_enable(self):
        self.plugin.enable = lambda: setattr(self, 'enabled', True)
        self.plugin.enable_wrapper()
        self.assert_(self.enabled, True)

    def test_disable_wrapper_calls_disable(self):
        self.plugin.disable = lambda: setattr(self, 'disabled', True)
        self.plugin.disable_wrapper()
        self.assert_(self.disabled, True)


class PluginManagerInitialStateTests(unittest.TestCase):

    def setUp(self):
        self.pm = PluginManager()

    def test_locations_is_empty_list(self):
        self.assertEqual(self.pm.locations, [])

    def test_plugins_is_empty_list(self):
        self.assertEqual(self.pm.plugins, [])

    def test_application_version_is_zeroes(self):
        self.assertEqual(self.pm.application_version, '0.0.0')

    def test_plugin_files_is_empty(self):
        self.assertEqual(self.pm.plugin_files, [])

    def test_plugin_arguments_is_empty(self):
        self.assertEqual(self.pm.plugin_arguments, [])

    def test_plugin_keyword_arguments_is_empty(self):
        self.assertEqual(self.pm.plugin_keyword_arguments, {})


class PluginManagerTests(unittest.TestCase):

    def setUp(self):
        self.pm = PluginManager()
        self.pm.locations = ['test-plugins', 'not-exist']
        self.pm.plugin_arguments = ('fooarg',)
        self.pm.plugin_keyword_arguments = { 'bar': 'bararg' }

        self.files = sorted(['test-plugins/hello_plugin.py',
                             'test-plugins/aaa_hello_plugin.py',
                             'test-plugins/oldhello_plugin.py',
                             'test-plugins/wrongversion_plugin.py'])

    def test_finds_the_right_plugin_files(self):
        self.assertEqual(self.pm.find_plugin_files(), self.files)

    def test_plugin_files_attribute_implicitly_searches(self):
        self.assertEqual(self.pm.plugin_files, self.files)

    def test_loads_hello_plugin(self):
        plugins = self.pm.load_plugins()
        self.assertEqual(len(plugins), 1)
        self.assertEqual(plugins[0].name, 'Hello')

    def test_plugins_attribute_implicitly_searches(self):
        self.assertEqual(len(self.pm.plugins), 1)
        self.assertEqual(self.pm.plugins[0].name, 'Hello')

    def test_initializes_hello_with_correct_args(self):
        plugin = self.pm['Hello']
        self.assertEqual(plugin.foo, 'fooarg')
        self.assertEqual(plugin.bar, 'bararg')

    def test_raises_keyerror_for_unknown_plugin(self):
        self.assertRaises(KeyError, self.pm.__getitem__, 'Hithere')

    def test_enable_plugins_enables_all_plugins(self):
        enabled = set()
        for plugin in self.pm.plugins:
            plugin.enable = lambda: enabled.add(plugin)
        self.pm.enable_plugins()
        self.assertEqual(enabled, set(self.pm.plugins))

    def test_disable_plugins_disables_all_plugins(self):
        disabled = set()
        for plugin in self.pm.plugins:
            plugin.disable = lambda: disabled.add(plugin)
        self.pm.disable_plugins()
        self.assertEqual(disabled, set(self.pm.plugins))


class PluginManagerCompatibleApplicationVersionTests(unittest.TestCase):

    def setUp(self):
        self.pm = PluginManager()
        self.pm.application_version = '1.2.3'

    def test_rejects_zero(self):
        self.assertFalse(self.pm.compatible_version('0'))

    def test_rejects_two(self):
        self.assertFalse(self.pm.compatible_version('2'))

    def test_rejects_one_two_four(self):
        self.assertFalse(self.pm.compatible_version('1.2.4'))

    def test_accepts_one(self):
        self.assert_(self.pm.compatible_version('1'))

    def test_accepts_one_two_three(self):
        self.assert_(self.pm.compatible_version('1.2.3'))

