# Copyright (C) 2010  Lars Wirzenius
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


class ForgetPolicyTests(unittest.TestCase):

    def setUp(self):
        self.fp = obnamlib.ForgetPolicy()

    def test_raises_error_for_empty_string(self):
        self.assertRaises(obnamlib.Error, self.fp.parse, '')

    def test_raises_error_for_unknown_period(self):
        self.assertRaises(obnamlib.Error, self.fp.parse, '7x')

    def test_raises_error_if_period_is_duplicated(self):
        self.assertRaises(obnamlib.Error, self.fp.parse, '1h,2h')

    def test_raises_error_rules_not_separated_by_comma(self):
        self.assertRaises(obnamlib.Error, self.fp.parse, '1h 2d')

    def test_parses_single_rule(self):
        self.assertEqual(self.fp.parse('7d'),
                         { 'hourly': 0,
                           'daily': 7,
                           'weekly': 0,
                           'monthly': 0,
                           'yearly': 0 })

    def test_parses_multiple_rules(self):
        self.assertEqual(self.fp.parse('1h,2d,3w,4m,255y'),
                         { 'hourly': 1,
                           'daily': 2,
                           'weekly': 3,
                           'monthly': 4,
                           'yearly': 255 })

