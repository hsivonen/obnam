# Copyright (C) 2008  Lars Wirzenius <liw@liw.fi>
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


class MappingTests(unittest.TestCase):

    def setUp(self):
        self.mapping = obnamlib.Mapping()
        
    def test_is_initially_empty(self):
        self.assertEqual(self.mapping.items(), [])
        
    def test_adds_mapping_correctly(self):
        self.mapping["foo"] = "bar"
        self.assertEqual(self.mapping.items(), [("foo", "bar")])
        
    def test_reuses_instance_when_adding_mapping_to_same_value_twice(self):
        self.mapping["foo"] = "bar"
        self.mapping["foobar"] = "bar"
        self.assert_(self.mapping["foo"] is self.mapping["foobar"])
