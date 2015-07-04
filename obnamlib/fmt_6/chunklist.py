# Copyright 2010-2015  Lars Wirzenius
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


import struct
import tracing

import obnamlib


class ChunkList(obnamlib.RepositoryTree):

    '''Repository's list of chunks.

    The list maps a chunk id to its checksum.

    The list is implemented as a B-tree, with the 64-bit chunk id as the
    key, and the checksum as the value.

    '''

    def __init__(self, fs, node_size, upload_queue_size, lru_size, hooks):
        tracing.trace('new ChunkList')
        self.fmt = '!Q'
        self.key_bytes = struct.calcsize(self.fmt)
        obnamlib.RepositoryTree.__init__(
            self, fs, 'chunklist', self.key_bytes, node_size,
            upload_queue_size, lru_size, hooks)
        self.keep_just_one_tree = True

    def key(self, chunk_id):
        return struct.pack(self.fmt, chunk_id)

    def add(self, chunk_id, checksum):
        tracing.trace('chunk_id=%s', chunk_id)
        tracing.trace('checksum=%s', repr(checksum))
        self.start_changes()
        self.tree.insert(self.key(chunk_id), checksum)

    def get_checksum(self, chunk_id):
        if self.init_forest() and self.forest.trees:
            t = self.forest.trees[-1]
            return t.lookup(self.key(chunk_id))
        raise KeyError(chunk_id)

    def remove(self, chunk_id):
        tracing.trace('chunk_id=%s', chunk_id)
        self.start_changes()
        key = self.key(chunk_id)
        self.tree.remove_range(key, key)
