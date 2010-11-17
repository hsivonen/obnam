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


import hashlib
import struct
import random

import obnamlib


class ClientList(obnamlib.StoreTree):

    '''Store list of clients.
    
    The list maps a client name to an arbitrary (string) identifier,
    which is unique within the store.
    
    The list is implemented as a B-tree, with a three-part key:
    MD5 of client name, 1-byte value type field, and 64-bit index,
    for hash collisions.
    
    Value type 0 is the full client name; this is used for detecting
    (very unlikely) hash collisions. Value type 1 is the actual 64-bit
    identifier.
    
    The index is 0 for the first client whose name results in a
    given MD5 checksum, and a random integer after that.
    
    The client's identifier is a string catenation of the MD5 of the name
    (in hex) and the index (in hex).
    
    '''

    type_name = 0
    type_id = 1
    max_index = 2**64 - 1

    def __init__(self, fs, node_size, upload_queue_size, lru_size):
        self.hash_len = len(self.hashfunc(''))
        self.fmt = '!%dsBQ' % self.hash_len
        self.key_bytes = len(self.key('', 0, 0))
        self.minkey = self.hashkey('\x00' * self.hash_len, 0, 0)
        self.maxkey = self.hashkey('\xff' * self.hash_len, 255, self.max_index)
        obnamlib.StoreTree.__init__(self, fs, 'clientlist', self.key_bytes, 
                                    node_size, upload_queue_size, lru_size)

    def hashfunc(self, string):
        return hashlib.new('md5', string).digest()

    def hexhashfunc(self, string):
        return self.hashfunc(string).encode('hex')

    def hashkey(self, h, value_type, index):
        return struct.pack(self.fmt, h, value_type, index)

    def key(self, client_name, value_type, index):
        h = self.hashfunc(client_name)
        return self.hashkey(h, value_type, index)

    def unkey(self, key):
        return struct.unpack(self.fmt, key)

    def client_id(self, client_name, index):
        return '%s%08x' % (self.hexhashfunc(client_name), index)

    def list_clients(self):
        if self.init_forest() and self.forest.trees:
            t = self.forest.trees[-1]
            return [v 
                    for k, v in t.lookup_range(self.minkey, self.maxkey)
                    if self.unkey(k)[1] == self.type_name]
        else:
            return []

    def find_client_index(self, t, client_name):
        minkey = self.key(client_name, 0, 0)
        maxkey = self.key(client_name, 255, self.max_index)
        for k, v in t.lookup_range(minkey, maxkey):
            checksum, value_type, index = self.unkey(k)
            if value_type == self.type_name and v == client_name:
                return index
        return None

    def get_client_id(self, client_name):
        if not self.init_forest() or not self.forest.trees:
            return None
        
        t = self.forest.trees[-1]
        index = self.find_client_index(t, client_name)
        if index is None:
            return None
        return self.client_id(client_name, index)

    def add_client(self, client_name):
        self.require_forest()
        if not self.forest.trees:
            t = self.forest.new_tree()
        else:
            t = self.forest.new_tree(old=self.forest.trees[-1])

        if self.find_client_index(t, client_name) is None:
            index = 0
            while True:
                k = self.key(client_name, self.type_name, index)
                try:
                    t.lookup(k)
                except KeyError:
                    break
                else:
                    index = random.randint(1, self.max_index)
            t.insert(self.key(client_name, self.type_name, index), 
                     client_name)
        
    def remove_client(self, client_name):
        self.require_forest()
        if self.forest.trees:
            t = self.forest.new_tree(old=self.forest.trees[-1])
            index = self.find_client_index(t, client_name)
            if index is not None:
                t.remove(self.key(client_name, self.type_name, index))

