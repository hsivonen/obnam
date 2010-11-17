# Copyright 2010  Lars Wirzenius
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

import obnamlib


class ChunkGroupTree(obnamlib.StoreTree):

    '''Store chunk groups.

    A chunk group maps an identifier (integer) to a list of chunk ids
    (integers).

    '''
    
    # We store things using the chunk group id as tkey key. The ids of
    # the chunks are stored as the value, as a blob, using struct.

    def __init__(self, fs, node_size, upload_queue_size, lru_size):
        obnamlib.StoreTree.__init__(self, fs, 'chunkgroups', 
                                    len(self.key(0)), node_size, 
                                    upload_queue_size, lru_size)
        self.max_id = 2**64 - 1

    def key(self, cgid):
        return struct.pack('!Q', cgid)

    def unkey(self, key):
        return struct.unpack('!Q', key)[0]

    def blob(self, chunkids):
        return struct.pack('!' + 'Q' * len(chunkids), *chunkids)
        
    def unblob(self, blob):
        n = len(blob) / struct.calcsize('Q')
        return struct.unpack('!' + 'Q' * n, blob)

    def group_exists(self, cgid):
        '''Does a chunk group exist?'''
        if self.init_forest() and self.forest.trees:
            t = self.forest.trees[-1]
            try:
                t.lookup(self.key(cgid))
            except KeyError:
                pass
            else:
                return True
        return False

    def list_chunk_groups(self):
        '''List all chunk group ids.'''
        if self.init_forest() and self.forest.trees:
            t = self.forest.trees[-1]
            pairs = t.lookup_range(self.key(0), self.key(self.max_id))
            return list(self.unkey(key) for key, value in pairs)
        else:
            return []

    def list_chunk_group_chunks(self, cgid):
        '''List all chunks in a chunk group.'''
        if self.init_forest() and self.forest.trees:
            t = self.forest.trees[-1]
            blob = t.lookup(self.key(cgid))
            return list(self.unblob(blob))
        else:
            return []

    def add(self, cgid, chunkids):
        '''Add a chunk group.'''
        self.require_forest()
        if self.forest.trees:
            t = self.forest.trees[-1]
        else:
            t = self.forest.new_tree()
        blob = self.blob(chunkids)
        t.insert(self.key(cgid), blob)

    def remove(self, cgid):
        '''Remove a chunk group.'''
        self.require_forest()
        if self.forest.trees:
            t = self.forest.trees[-1]
            t.remove(self.key(cgid))

