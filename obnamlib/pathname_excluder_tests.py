# Copyright (C) 2015  Lars Wirzenius
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


class PathnameExcluderTest(unittest.TestCase):

    def test_allows_everything_when_nothing_is_excluded(self):
        excluder = obnamlib.PathnameExcluder()
        self.assertEqual(excluder.exclude('/foo'), (False, None))

    def test_excludes_pathname_matching_exclusion_pattern(self):
        excluder = obnamlib.PathnameExcluder()
        excluder.exclude_regexp('foo')
        excluded, pattern = excluder.exclude('/foobar')
        self.assertTrue(excluded)
        self.assertEqual(pattern, 'foo')

    def test_allows_pathname_matching_both_exclusion_and_inclusion(self):
        excluder = obnamlib.PathnameExcluder()
        excluder.exclude_regexp('foo')
        excluder.allow_regexp('oo')
        self.assertTrue(excluder.exclude('/foo'), (False, 'oo'))
