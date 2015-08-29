# Copyright (C) 2010-2015  Lars Wirzenius
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


import datetime
import unittest

import obnamlib


class ForgetPolicyParseTests(unittest.TestCase):

    def setUp(self):
        self.fp = obnamlib.ForgetPolicy()

    def test_raises_error_for_empty_string(self):
        self.assertRaises(obnamlib.ObnamError, self.fp.parse, '')

    def test_raises_error_for_unknown_period(self):
        self.assertRaises(obnamlib.ObnamError, self.fp.parse, '7x')

    def test_raises_error_if_period_is_duplicated(self):
        self.assertRaises(obnamlib.ObnamError, self.fp.parse, '1h,2h')

    def test_raises_error_rules_not_separated_by_comma(self):
        self.assertRaises(obnamlib.ObnamError, self.fp.parse, '1h 2d')

    def test_parses_single_rule(self):
        self.assertEqual(
            self.fp.parse('7d'),
            {
                'hourly': 0,
                'daily': 7,
                'weekly': 0,
                'monthly': 0,
                'yearly': 0
            })

    def test_parses_multiple_rules(self):
        self.assertEqual(
            self.fp.parse('1h,2d,3w,4m,255y'),
            {
                'hourly': 1,
                'daily': 2,
                'weekly': 3,
                'monthly': 4,
                'yearly': 255
            })


class ForgetPolicyMatchTests(unittest.TestCase):

    def setUp(self):
        self.fp = obnamlib.ForgetPolicy()

    def match2(self, spec, times):
        rules = self.fp.parse(spec)
        return [dt for _, dt in self.fp.match(rules, list(enumerate(times)))]

    def test_hourly_matches(self):
        h0m0 = datetime.datetime(2000, 1, 1, 0, 0)
        h0m59 = datetime.datetime(2000, 1, 1, 0, 59)
        h1m0 = datetime.datetime(2000, 1, 1, 1, 0)
        h1m59 = datetime.datetime(2000, 1, 1, 1, 59)
        self.assertEqual(self.match2('1h', [h0m0, h0m59, h1m0, h1m59]),
                         [h1m59])

    def test_two_hourly_matches(self):
        h0m0 = datetime.datetime(2000, 1, 1, 0, 0)
        h0m59 = datetime.datetime(2000, 1, 1, 0, 59)
        h1m0 = datetime.datetime(2000, 1, 1, 1, 0)
        h1m59 = datetime.datetime(2000, 1, 1, 1, 59)
        self.assertEqual(self.match2('2h', [h0m0, h0m59, h1m0, h1m59]),
                         [h0m59, h1m59])

    def test_daily_matches(self):
        d1h0 = datetime.datetime(2000, 1, 1, 0, 0)
        d1h23 = datetime.datetime(2000, 1, 1, 23, 0)
        d2h0 = datetime.datetime(2000, 1, 2, 0, 0)
        d2h23 = datetime.datetime(2000, 1, 2, 23, 0)
        self.assertEqual(self.match2('1d', [d1h0, d1h23, d2h0, d2h23]),
                         [d2h23])

    # Not testing weekly matching, since I can't figure out to make
    # a sensible test case right now.

    def test_monthly_matches(self):
        m1d1 = datetime.datetime(2000, 1, 1, 0, 0)
        m1d28 = datetime.datetime(2000, 1, 28, 0, 0)
        m2d1 = datetime.datetime(2000, 2, 1, 0, 0)
        m2d28 = datetime.datetime(2000, 2, 28, 0, 0)
        self.assertEqual(self.match2('1m', [m1d1, m1d28, m2d1, m2d28]),
                         [m2d28])

    def test_yearly_matches(self):
        y1m1 = datetime.datetime(2000, 1, 1, 0, 0)
        y1m12 = datetime.datetime(2000, 12, 1, 0, 0)
        y2m1 = datetime.datetime(2001, 1, 1, 0, 0)
        y2m12 = datetime.datetime(2001, 12, 1, 0, 0)
        self.assertEqual(self.match2('1y', [y1m1, y1m12, y2m1, y2m12]),
                         [y2m12])

    def test_hourly_and_daily_match_together(self):
        d1h0m0 = datetime.datetime(2000, 1, 1, 0, 0)
        d1h0m1 = datetime.datetime(2000, 1, 1, 0, 1)
        d2h0m0 = datetime.datetime(2000, 1, 2, 0, 0)
        d2h0m1 = datetime.datetime(2000, 1, 2, 0, 1)
        d3h0m0 = datetime.datetime(2000, 1, 3, 0, 0)
        d3h0m1 = datetime.datetime(2000, 1, 3, 0, 1)
        genlist = list(enumerate([d1h0m0, d1h0m1, d2h0m0, d2h0m1,
                                  d3h0m0, d3h0m1]))
        rules = self.fp.parse('1h,2d')
        self.assertEqual([dt for _, dt in self.fp.match(rules, genlist)],
                         [d2h0m1, d3h0m1])

    def test_hourly_and_daily_together_when_only_daily_backups(self):
        d1 = datetime.datetime(2000, 1, 1, 0, 0)
        d2 = datetime.datetime(2000, 1, 2, 0, 0)
        d3 = datetime.datetime(2000, 1, 3, 0, 0)
        self.assertEqual(self.match2('10h,1d', [d1, d2, d3]),
                         [d1, d2, d3])
