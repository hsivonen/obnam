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


class ObjectSerialisationRoundtripTests(unittest.TestCase):

    def test_handles_an_int(self):
        blob = obnamlib.serialise_object(42)
        self.assertEqual(obnamlib.deserialise_object(blob), 42)

    def test_handles_a_boolean_true(self):
        blob = obnamlib.serialise_object(True)
        self.assertEqual(obnamlib.deserialise_object(blob), True)

    def test_handles_a_boolean_false(self):
        blob = obnamlib.serialise_object(False)
        self.assertEqual(obnamlib.deserialise_object(blob), False)

    def test_handles_None(self):
        blob = obnamlib.serialise_object(None)
        self.assertEqual(obnamlib.deserialise_object(blob), None)

    def test_handles_string(self):
        blob = obnamlib.serialise_object('foo')
        self.assertEqual(obnamlib.deserialise_object(blob), 'foo')

    def test_handles_empty_string(self):
        blob = obnamlib.serialise_object('')
        self.assertEqual(obnamlib.deserialise_object(blob), '')

    def test_handles_list(self):
        blob = obnamlib.serialise_object([1, 2, 3])
        self.assertEqual(obnamlib.deserialise_object(blob), [1, 2, 3])

    def test_handles_empty_list(self):
        blob = obnamlib.serialise_object([])
        self.assertEqual(obnamlib.deserialise_object(blob), [])

    def test_handles_dict(self):
        blob = obnamlib.serialise_object({'foo': 'bar'})
        self.assertEqual(obnamlib.deserialise_object(blob), {'foo': 'bar'})

    def test_handles_empty_dict(self):
        blob = obnamlib.serialise_object({})
        self.assertEqual(obnamlib.deserialise_object(blob), {})

    def test_handles_more_complicated_object(self):
        obj = {
            'zero': 0,
            'true': True,
            'string': 'abc\0def',
            'list': ['foo'],
            'dict': {
                'one': 0,
            },
        }
        blob = obnamlib.serialise_object(obj)
        self.assertEqual(obnamlib.deserialise_object(blob), obj)
