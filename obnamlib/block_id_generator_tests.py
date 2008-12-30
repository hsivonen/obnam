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


class BlockIdGeneratorTests(unittest.TestCase):

    def setUp(self):
        self.idgen = obnamlib.BlockIdGenerator(levels=2, per_level=3)

    def test_has_no_prefix_initially(self):
        self.assertEqual(self.idgen.prefix, None)

    def test_counters_start_at_zero_initially(self):
        self.assertEqual(self.idgen.counters, [0] * self.idgen.levels)

    def test_generates_a_prefix(self):
        self.idgen.new_id()
        self.assertNotEqual(self.idgen.prefix, None)
        
    def test_generates_id_that_starts_with_prefix(self):
        id = self.idgen.new_id()
        self.assert_(id.startswith(self.idgen.prefix))

    def test_first_new_id_uses_zeroes(self):
        id = self.idgen.new_id()
        self.assertEqual(id, self.idgen.prefix + "/0" * self.idgen.levels)

    def test_new_id_increments_counters(self):
        id = self.idgen.new_id()
        self.assertEqual(self.idgen.counters, 
                         ([0] * (self.idgen.levels-1)) + [1])

    def test_second_new_id_uses_incremented_counters(self):
        self.idgen.new_id()
        suffix = "/".join("%d" % n for n in self.idgen.counters)
        id = self.idgen.new_id()
        self.assertEqual(id, "%s/%s" % (self.idgen.prefix, suffix))

    def test_leaf_counter_overflows_correctly(self):
        self.idgen.counters = [0, self.idgen.per_level]
        self.idgen.new_id()
        self.assertEqual(self.idgen.counters[-1], 0)
        self.assertEqual(self.idgen.counters[-2], 1)

    def test_generates_new_prefix_after_topmost_counter_overflows(self):
        self.idgen.new_id()
        initial_prefix = self.idgen.prefix
        self.idgen.counters = [self.idgen.per_level] * self.idgen.levels
        self.idgen.new_id()
        self.assertNotEqual(initial_prefix, self.idgen.prefix)
