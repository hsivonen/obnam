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


class ClientList(obnamlib.RepositoryTree):

    '''Repository's list of clients.
    
    The list maps a client name to an arbitrary (string) identifier,
    which is unique within the repository.
    
    The list is implemented as a B-tree, with a two-part key:
    128-bit MD5 of client name, and 64-bit unique identifier.
    The value is the client name.
    
    The client's identifier is a random, unique 64-bit integer.
    
    '''

    def __init__(self, fs, node_size, upload_queue_size, lru_size, hooks):
        self.hash_len = len(self.hashfunc(''))
        self.fmt = '!%dsQ' % self.hash_len
        self.key_bytes = len(self.key('', 0))
        self.minkey = self.hashkey('\x00' * self.hash_len, 0)
        self.maxkey = self.hashkey('\xff' * self.hash_len, obnamlib.MAX_ID)
        obnamlib.RepositoryTree.__init__(self, fs, 'clientlist', 
                                         self.key_bytes, node_size, 
                                         upload_queue_size, lru_size, hooks)
        self.keep_just_one_tree = True

    def hashfunc(self, string):
        return hashlib.new('md5', string).digest()

    def hashkey(self, namehash, client_id):
        return struct.pack(self.fmt, namehash, client_id)

    def key(self, client_name, client_id):
        h = self.hashfunc(client_name)
        return self.hashkey(h, client_id)

    def unkey(self, key):
        return struct.unpack(self.fmt, key)

    def random_id(self):
        return random.randint(0, obnamlib.MAX_ID)

    def list_clients(self):
        if self.init_forest() and self.forest.trees:
            t = self.forest.trees[-1]
            return [v for k, v in t.lookup_range(self.minkey, self.maxkey)]
        else:
            return []

    def find_client_id(self, t, client_name):
        minkey = self.key(client_name, 0)
        maxkey = self.key(client_name, obnamlib.MAX_ID)
        for k, v in t.lookup_range(minkey, maxkey):
            checksum, client_id = self.unkey(k)
            if v == client_name:
                return client_id
        return None

    def get_client_id(self, client_name):
        if not self.init_forest() or not self.forest.trees:
            return None
        t = self.forest.trees[-1]
        return self.find_client_id(t, client_name)

    def add_client(self, client_name):
        self.start_changes()
        if self.find_client_id(self.tree, client_name) is None:
            while True:
                candidate_id = self.random_id()
                key = self.key(client_name, candidate_id)
                try:
                    self.tree.lookup(key)
                except KeyError:
                    break
            self.tree.insert(self.key(client_name, candidate_id), client_name)
        
    def remove_client(self, client_name):
        self.start_changes()
        client_id = self.find_client_id(self.tree, client_name)
        if client_id is not None:
            self.tree.remove(self.key(client_name, client_id))

