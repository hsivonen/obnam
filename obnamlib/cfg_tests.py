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


class ConfigurationTests(unittest.TestCase):

    def setUp(self):
        self.cfg = obnamlib.Configuration([])
        self.cfg.new_boolean(['foo'], 'foo help')
        self.cfg.new_string(['bar'], 'bar help')
        self.cfg.new_list(['list'], 'list help')

    def test_has_no_args_by_default(self):
        self.assertEqual(self.cfg.args, [])

    def test_sets_boolean_to_false_by_default(self):
        self.assertEqual(self.cfg['foo'], False)

    def test_sets_string_to_empty_by_default(self):
        self.assertEqual(self.cfg['bar'], '')

    def test_sets_list_to_empty_list_by_default(self):
        self.assertEqual(self.cfg['list'], [])

    def test_parses_command_line(self):
        self.cfg.load(args=['--foo', '--bar=foobar', '--list=a', '--list=b,c'])
        self.assertEqual(self.cfg['foo'], True)
        self.assertEqual(self.cfg['bar'], 'foobar')
        self.assertEqual(self.cfg['list'], ['a', 'b', 'c'])

    def test_sets_value(self):
        self.cfg['foo'] = True
        self.assertEqual(self.cfg['foo'], True)

