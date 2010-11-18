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


class ChecksumTree(obnamlib.StoreTree):

    '''Store map of checksum to integer id.

    The checksum might be, for example, an MD5 one (as returned by
    hashlib.md5().digest()). The id would be a chunk or chunk group
    id.

    '''

    def __init__(self, fs, name, checksum_length, node_size, 
                 upload_queue_size, lru_size):
        self.sumlen = checksum_length
        key_bytes = len(self.key('', 0))
        obnamlib.StoreTree.__init__(self, fs, name, key_bytes, node_size, 
                                    upload_queue_size, lru_size)
        self.max_id = 2**64 - 1

    def key(self, checksum, number):
        return struct.pack('!%dsQ' % self.sumlen, checksum, number)

    def unkey(self, key):
        return struct.unpack('!%dsQ' % self.sumlen, key)

    def add(self, checksum, identifier):
        self.require_forest()
        key = self.key(checksum, identifier)
        if self.forest.trees:
            t = self.forest.trees[-1]
        else:
            t = self.forest.new_tree()
        t.insert(key, '')

    def find(self, checksum):
        if self.init_forest() and self.forest.trees:
            t = self.forest.trees[-1]
            pairs = t.lookup_range(self.key(checksum, 0),
                                   self.key(checksum, self.max_id))
            return [self.unkey(key)[1] for key, value in pairs]
        else:
            return []

    def remove(self, checksum, identifier):
        self.require_forest()
        if self.forest.trees:
            t = self.forest.new_tree(self.forest.trees[-1])
            t.remove(self.key(checksum, identifier))

