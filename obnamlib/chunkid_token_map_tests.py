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


class ChunkIdTokenMapTests(unittest.TestCase):

    def setUp(self):
        self.map = obnamlib.ChunkIdTokenMap()

    def test_is_empty_initially(self):
        self.assertEqual(list(self.map), [])

    def test_adds_a_pair(self):
        chunk_id = '123'
        token = 'foobar'
        self.map.add(chunk_id, token)
        self.assertEqual(list(self.map), [(chunk_id, token)])
