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


class GATreeTests(unittest.TestCase):

    def setUp(self):
        self.blob_store = obnamlib.BlobStore()
        self.blob_store.set_bag_store(DummyBagStore())

        self.tree = obnamlib.GATree()
        self.tree.set_blob_store(self.blob_store)

    def test_has_no_root_dir_initially(self):
        self.assertEqual(self.tree.get_directory('/'), None)

    def test_sets_root_dir(self):
        dir_obj = obnamlib.GADirectory()
        self.tree.set_directory('/', dir_obj)
        self.assertEqual(self.tree.get_directory('/'), dir_obj)

    def test_stores_objects_persistently(self):
        orig = obnamlib.GADirectory()
        self.tree.set_directory('/foo/bar', orig)
        self.tree.flush()

        tree2 = obnamlib.GATree()
        tree2.set_blob_store(self.blob_store)
        tree2.set_root_directory_id(self.tree.get_root_directory_id())
        retrieved = tree2.get_directory('/foo/bar')
        self.assertEqual(orig.as_dict(), retrieved.as_dict())


class DummyBagStore(object):

    def __init__(self):
        self._bags = {}
        self._prev_id = 0

    def reserve_bag_id(self):
        self._prev_id += 1
        return self._prev_id

    def put_bag(self, bag):
        self._bags[bag.get_id()] = bag

    def has_bag(self, bag_id):
        return bag_id in self._bags

    def get_bag(self, bag_id):
        return self._bags[bag_id]
