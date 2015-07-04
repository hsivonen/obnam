# Copyright 2010-2014  Lars Wirzenius
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

    def test_returns_an_int(self):
        self.assert_(isinstance(self.p.parse('123'), int))

    def test_parses_unadorned_size_using_default_unit(self):
        self.p.set_default_unit('KiB')
        self.assertEqual(self.p.parse('123'), 123 * 1024)

    def test_parses_size_with_byte_unit(self):
        self.assertEqual(self.p.parse('123 B'), 123)

    def test_parses_size_with_kilo_unit(self):
        self.assertEqual(self.p.parse('123 k'), 123 * 1000)

    def test_parses_size_with_kilobyte_unit(self):
        self.assertEqual(self.p.parse('123 kB'), 123 * 1000)

    def test_parses_size_with_kibibyte_unit(self):
        self.assertEqual(self.p.parse('123 KiB'), 123 * 1024)

    def test_parses_size_with_mega_unit(self):
        self.assertEqual(self.p.parse('123 m'), 123 * 1000**2)

    def test_parses_size_with_megabyte_unit(self):
        self.assertEqual(self.p.parse('123 MB'), 123 * 1000**2)

    def test_parses_size_with_mebibyte_unit(self):
        self.assertEqual(self.p.parse('123 MiB'), 123 * 1024**2)

    def test_parses_size_with_giga_unit(self):
        self.assertEqual(self.p.parse('123 g'), 123 * 1000**3)

    def test_parses_size_with_gigabyte_unit(self):
        self.assertEqual(self.p.parse('123 GB'), 123 * 1000**3)

    def test_parses_size_with_gibibyte_unit(self):
        self.assertEqual(self.p.parse('123 GiB'), 123 * 1024**3)

    def test_raises_error_for_empty_string(self):
        self.assertRaises(obnamlib.SizeSyntaxError, self.p.parse, '')

    def test_raises_error_for_missing_size(self):
        self.assertRaises(obnamlib.SizeSyntaxError, self.p.parse, 'KiB')

    def test_raises_error_for_bad_unit(self):
        self.assertRaises(obnamlib.SizeSyntaxError, self.p.parse, '1 km')

    def test_raises_error_for_bad_unit_thats_similar_to_real_one(self):
        self.assertRaises(obnamlib.UnitNameError, self.p.parse, '1 ib')

    def test_raises_error_for_bad_default_unit(self):
        self.assertRaises(obnamlib.UnitNameError,
                          self.p.set_default_unit, 'km')

    def test_size_syntax_error_includes_input_string(self):
        text = 'asdf asdf'
        e = obnamlib.SizeSyntaxError(size=text)
        self.assert_(text in str(e), str(e))

    def test_unit_name_error_includes_input_string(self):
        text = 'asdf asdf'
        e = obnamlib.UnitNameError(unit=text)
        self.assert_(text in str(e), str(e))
