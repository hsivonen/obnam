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


import datetime
import unittest

import obnamlib


class ForgetPolicyParseTests(unittest.TestCase):

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


times = []
for year in range(2009, 2010):
    for month in range(1, 13):
        for day in range(1, 29):
            for hour in range(24):
                for minute in range(58, 60):
                    dt = datetime.datetime(year, month, day,
                                            hour, minute)
                    times.append(dt)
enumerated_times = list(enumerate(times))


class ForgetPolicyMatchTests(unittest.TestCase):

    def setUp(self):
        self.fp = obnamlib.ForgetPolicy()

    def match(self, spec):
        rules = self.fp.parse(spec)
        return [time 
                for i, time in self.fp.match(rules, enumerated_times)]

    def test_hourly_matches(self):
        self.assertEqual(self.match('1h'),
                         [dt for dt in times if dt.minute == 59][-1:])

    def test_daily_matches(self):
        self.assertEqual(self.match('1d'),
                         [dt for dt in times 
                          if dt.hour == 23 and dt.minute == 59][-1:])

    # Not testing weekly matching, since I can't figure out to make
    # a sensible test case right now.

    def test_monthly_matches(self):
        self.assertEqual(self.match('1m'),
                         [dt for dt in times 
                          if dt.day == 28 and 
                             dt.hour == 23 and 
                             dt.minute == 59][-1:])

    def test_yearly_matches(self):
        self.assertEqual(self.match('1y'),
                         [dt for dt in times 
                          if dt.month == 12 and
                             dt.day == 28 and 
                             dt.hour == 23 and 
                             dt.minute == 59][-1:])

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
        self.assertEqual([dt for genid, dt in self.fp.match(rules, genlist)],
                         [d2h0m1, d3h0m1])

