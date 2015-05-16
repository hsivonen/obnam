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


import errno
import os
import random

import obnamlib


class GAChunkStore(object):

    def __init__(self):
        self._fs = None
        self._dirname = 'chunk-store'
        self._bag = None
        self._bag_store = obnamlib.BagStore()
        self._max_bag_size = None

    def set_fs(self, fs):
        self._fs = fs
        self._bag_store.set_location(fs, self._dirname)

    def set_max_chunk_size(self, max_chunk_size):
        self._max_bag_size = max_chunk_size

    def put_chunk_content(self, content):
        self._fs.create_and_init_toplevel(self._dirname)
        if self._bag is None:
            self._bag = self._new_bag()
        chunk_id = self._bag.append(content)
        if self._bag_is_big_enough(self._bag):
            self.flush_chunks()
        return chunk_id

    def _new_bag(self):
        bag = obnamlib.Bag()
        bag.set_id(self._bag_store.reserve_bag_id())
        return bag

    def _bag_is_big_enough(self, bag):
        approx_size = sum(len(bag[i]) for i in range(len(bag)))
        return self._max_bag_size is None or approx_size >= self._max_bag_size

    def flush_chunks(self):
        if self._bag:
            self._bag_store.put_bag(self._bag)
            self._bag = None

    def get_chunk_content(self, chunk_id):
        bag_id, index = obnamlib.parse_object_id(chunk_id)
        try:
            bag = self._bag_store.get_bag(bag_id)
        except (IOError, OSError) as e:
            if e.errno == errno.ENOENT:
                raise obnamlib.RepositoryChunkDoesNotExist(
                    chunk_id=chunk_id,
                    filename=None)
            raise
        return bag[index]

    def has_chunk(self, chunk_id):
        bag_id, _ = obnamlib.parse_object_id(chunk_id)
        return self._bag_store.has_bag(bag_id)

    def remove_chunk(self, chunk_id):
        bag_id, _ = obnamlib.parse_object_id(chunk_id)
        if self._bag is not None and bag_id == self._bag.get_id():
            self._bag = None
        else:
            try:
                self._bag_store.remove_bag(bag_id)
            except (IOError, OSError) as e:
                if e.errno == errno.ENOENT:
                    raise obnamlib.RepositoryChunkDoesNotExist(
                        chunk_id=chunk_id,
                        filename=None)
                raise

    def get_chunk_ids(self):
        result = []
        if self._bag:
            result += self._get_chunk_ids_from_bag(self._bag)

        for bag_id in self._bag_store.get_bag_ids():
            bag = self._bag_store.get_bag(bag_id)
            result += self._get_chunk_ids_from_bag(bag)

        return result

    def _get_chunk_ids_from_bag(self, bag):
        return [obnamlib.make_object_id(bag.get_id(), i)
                for i in range(len(bag))]
