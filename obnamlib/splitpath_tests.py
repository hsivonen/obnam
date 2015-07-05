# Copyright 2015  Lars Wirzenius
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
#
# =*= License: GPL-3+ =*=


import unittest

import obnamlib


class SplitPathnameTests(unittest.TestCase):

    def test_raises_error_for_empty_pathname(self):
        self.assertRaises(Exception, obnamlib.split_pathname, '')

    def test_returns_rootdir_for_rootdir(self):
        self.assertEqual(obnamlib.split_pathname('/'), ['/'])

    def test_returns_dir_for_relative_dir(self):
        self.assertEqual(obnamlib.split_pathname('bin'), ['bin'])

    def test_returns_root_and_dir_for_slash_bin(self):
        self.assertEqual(obnamlib.split_pathname('/bin'), ['/', 'bin'])

    def test_returns_root_and_dir_for_slash_bin_slash(self):
        self.assertEqual(obnamlib.split_pathname('/bin/'), ['/', 'bin'])

    def test_returns_all_components_for_long_pathname(self):
        self.assertEqual(
            obnamlib.split_pathname('/usr/share/doc'),
            ['/', 'usr', 'share', 'doc'])
