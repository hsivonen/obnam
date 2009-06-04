# Copyright (C) 2009  Lars Wirzenius <liw@liw.fi>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.


import unittest

import obnamlib


class FormatSizeTests(unittest.TestCase):

    def test_zero_size_results_in_zero_bytes(self):
        self.assertEqual(obnamlib.format_size(0), "0 B")
        
    def test_one_byte(self):
        self.assertEqual(obnamlib.format_size(1), "1 B")
        
    def test_999_bytes_results_in_bytes(self):
        self.assertEqual(obnamlib.format_size(999), "999 B")
        
    def test_1000_bytes_results_in_kilobyte(self):
        self.assertEqual(obnamlib.format_size(1000), "1 kB")
        

class FormatTimeTests(unittest.TestCase):

    def test_zero_time_is_zero_seconds(self):
        self.assertEqual(obnamlib.format_time(0), "0 s")

    def test_one_second(self):
        self.assertEqual(obnamlib.format_time(1), "1 s")
        
    def test_59_seconds(self):
        self.assertEqual(obnamlib.format_time(59), "59 s")
        
    def test_60_seconds(self):
        self.assertEqual(obnamlib.format_time(60), "1 min")
        
    def test_61_seconds(self):
        self.assertEqual(obnamlib.format_time(61), "1 min 1 s")

