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


import shutil
import tempfile
import unittest

import obnamlib


class BagStoreTests(unittest.TestCase):

    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        self.fs = obnamlib.LocalFS(self.tempdir)
        self.store = obnamlib.BagStore()
        self.store.set_location(self.fs, '.')
        self.bag = obnamlib.Bag()
        bag_id = self.store.reserve_bag_id()
        self.bag.set_id(bag_id)

    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def assertEqualBags(self, a, b):
        self.assertEqual(a.get_id(), b.get_id())
        self.assertEqual(len(a), len(b))
        for i in range(len(a)):
            self.assertEqual(a[i], b[i])

    def test_stores_and_retrieves_an_empty_bag(self):
        self.store.put_bag(self.bag)
        new_bag = self.store.get_bag(self.bag.get_id())
        self.assertEqualBags(new_bag, self.bag)

    def test_stores_and_retrieves_a_full_bag(self):
        self.bag.append('foo')
        self.store.put_bag(self.bag)
        new_bag = self.store.get_bag(self.bag.get_id())
        self.assertEqualBags(new_bag, self.bag)

    def test_has_no_bags_initially(self):
        store = obnamlib.BagStore()
        store.set_location(self.fs, 'empty')
        self.assertEqual(list(store.get_bag_ids()), [])

    def test_has_a_put_bag(self):
        self.store.put_bag(self.bag)
        self.assertTrue(self.store.has_bag(self.bag.get_id()))

    def test_does_not_have_a_removed_bag(self):
        self.store.put_bag(self.bag)
        self.store.remove_bag(self.bag.get_id())
        self.assertFalse(self.store.has_bag(self.bag.get_id()))

    def test_lists_bag_that_has_been_put(self):
        self.store.put_bag(self.bag)
        self.assertEqual(list(self.store.get_bag_ids()), [self.bag.get_id()])

    def test_removes_bag(self):
        self.store.put_bag(self.bag)
        self.store.remove_bag(self.bag.get_id())
        self.assertEqual(list(self.store.get_bag_ids()), [])
