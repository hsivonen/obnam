# Copyright 2010  Lars Wirzenius
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


class ByteSizeParserTests(unittest.TestCase):

    def setUp(self):
        self.p = obnamlib.ByteSizeParser()
        
    def test_parses_zero(self):
        self.assertEqual(self.p.parse('0'), 0)
        
    def test_parses_unadorned_size_as_bytes(self):
        self.assertEqual(self.p.parse('123'), 123)
        
    def test_parses_unadorned_size_using_default_unit(self):
        self.p.set_default_unit('KiB')
        self.assertEqual(self.p.parse('123'), 123 * 1024)
        
    def test_parses_size_with_byte_unit(self):
        self.assertEqual(self.p.parse('123 B'), 123)
        
    def test_parses_size_with_kilobyte_unit(self):
        self.assertEqual(self.p.parse('123 kB'), 123 * 1000)
        
    def test_parses_size_with_kibibyte_unit(self):
        self.assertEqual(self.p.parse('123 KiB'), 123 * 1024)
        
    def test_parses_size_with_megabyte_unit(self):
        self.assertEqual(self.p.parse('123 MB'), 123 * 1000**2)
        
    def test_parses_size_with_mebibyte_unit(self):
        self.assertEqual(self.p.parse('123 MiB'), 123 * 1024**2)
        
    def test_parses_size_with_gigabyte_unit(self):
        self.assertEqual(self.p.parse('123 GB'), 123 * 1000**3)
        
    def test_parses_size_with_gibibyte_unit(self):
        self.assertEqual(self.p.parse('123 GiB'), 123 * 1024**3)

