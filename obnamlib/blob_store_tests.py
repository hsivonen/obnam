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


class BlobStoreTests(unittest.TestCase):

    def test_returns_None_for_missing_blob(self):
        bag_store = DummyBagStore()

        blob_store = obnamlib.BlobStore()
        blob_store.set_bag_store(bag_store)
        blob_id = obnamlib.make_object_id(123, 456)
        self.assertEqual(blob_store.get_blob(blob_id), None)

    def test_returns_existing_blob(self):
        bag_store = DummyBagStore()
        blob = 'blobby blob blob blob'

        blob_store = obnamlib.BlobStore()
        blob_store.set_bag_store(bag_store)
        blob_id = blob_store.put_blob(blob)
        retrieved = blob_store.get_blob(blob_id)
        self.assertEqual(blob, retrieved)

    def test_stores_blob_persistently(self):
        bag_store = DummyBagStore()
        blob = 'this is a blob, yes it is'

        blob_store = obnamlib.BlobStore()
        blob_store.set_bag_store(bag_store)
        blob_id = blob_store.put_blob(blob)
        blob_store.flush()

        blob_store_2 = obnamlib.BlobStore()
        blob_store_2.set_bag_store(bag_store)
        retrieved = blob_store_2.get_blob(blob_id)
        self.assertEqual(blob, retrieved)

    def test_gets_persistent_blob_twice(self):
        bag_store = DummyBagStore()
        blob = 'this is a blob, yes it is'

        blob_store = obnamlib.BlobStore()
        blob_store.set_bag_store(bag_store)
        blob_id = blob_store.put_blob(blob)
        blob_store.flush()

        blob_store_2 = obnamlib.BlobStore()
        blob_store_2.set_bag_store(bag_store)
        retrieved_1 = blob_store_2.get_blob(blob_id)
        retrieved_2 = blob_store_2.get_blob(blob_id)
        self.assertEqual(retrieved_1, retrieved_2)

    def test_obeys_max_bag_size(self):
        bag_store = DummyBagStore()
        blob = 'this is a blob, yes it is'

        blob_store = obnamlib.BlobStore()
        blob_store.set_bag_store(bag_store)

        blob_store.set_max_bag_size(len(blob))
        blob_store.put_blob(blob)
        self.assertTrue(bag_store.is_empty())

        blob_store.set_max_bag_size(1)
        blob_store.put_blob(blob)
        self.assertFalse(bag_store.is_empty())

    def test_finds_unflushed_blob(self):
        bag_store = DummyBagStore()
        blob = 'this is a blob, yes it is'

        blob_store = obnamlib.BlobStore()
        blob_store.set_bag_store(bag_store)
        blob_store.set_max_bag_size(len(blob))
        blob_id = blob_store.put_blob(blob)
        self.assertTrue(bag_store.is_empty())

        retrieved = blob_store.get_blob(blob_id)
        self.assertEqual(blob, retrieved)


class DummyBagStore(object):

    def __init__(self):
        self._bags = {}
        self._prev_id = 0

    def is_empty(self):
        return len(self._bags) == 0

    def reserve_bag_id(self):
        self._prev_id += 1
        return self._prev_id

    def put_bag(self, bag):
        self._bags[bag.get_id()] = bag

    def has_bag(self, bag_id):
        return bag_id in self._bags

    def get_bag(self, bag_id):
        return self._bags[bag_id]
