# Copyright 2014  Lars Wirzenius
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


class FirstError(obnamlib.StructuredError):

    msg = 'first with parameter foo set to {foo}'


class SecondError(obnamlib.StructuredError):

    msg = 'second'


class StructuredErrorTests(unittest.TestCase):

    def test_ids_differ_between_classes(self):
        first = FirstError()
        second = SecondError()
        self.assertNotEqual(first.id, second.id)

    def test_error_string_contains_id(self):
        first = FirstError(foo=None)
        self.assertTrue(first.id in str(first))

    def test_error_string_contains_parameter(self):
        first = FirstError(foo='xyzzy')
        self.assertTrue('xyzzy' in str(first))

    def test_returns_error_string_even_with_lacking_keywords(self):
        first = FirstError()
        self.assertTrue(first.id in str(first))
