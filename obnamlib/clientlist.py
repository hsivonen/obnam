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
import logging
import struct
import random
import tracing

import obnamlib


class ClientList(obnamlib.RepositoryTree):

    '''Repository's list of clients.

    The list maps a client name to an arbitrary (string) identifier,
    which is unique within the repository.

    The list is implemented as a B-tree, with a three-part key:
    128-bit MD5 of client name, 64-bit unique identifier, and subkey
    identifier. The value depends on the subkey: it's either the
    client's full name, or the public key identifier the client
    uses to encrypt their backups.

    The client's identifier is a random, unique 64-bit integer.

    '''

    # subkey values
    CLIENT_NAME = 0
    KEYID = 1
    SUBKEY_MAX = 255

    def __init__(self, fs, node_size, upload_queue_size, lru_size, hooks):
        tracing.trace('new ClientList')
        self.hash_len = len(self.hashfunc(''))
        self.fmt = '!%dsQB' % self.hash_len
        self.key_bytes = len(self.key('', 0, 0))
        self.minkey = self.hashkey('\x00' * self.hash_len, 0, 0)
        self.maxkey = self.hashkey('\xff' * self.hash_len, obnamlib.MAX_ID,
                                   self.SUBKEY_MAX)
        obnamlib.RepositoryTree.__init__(self, fs, 'clientlist',
                                         self.key_bytes, node_size,
                                         upload_queue_size, lru_size, hooks)
        self.keep_just_one_tree = True

    def hashfunc(self, string):
        return hashlib.new('md5', string).digest()

    def hashkey(self, namehash, client_id, subkey):
        return struct.pack(self.fmt, namehash, client_id, subkey)

    def key(self, client_name, client_id, subkey):
        h = self.hashfunc(client_name)
        return self.hashkey(h, client_id, subkey)

    def unkey(self, key):
        return struct.unpack(self.fmt, key)

    def random_id(self):
        return random.randint(0, obnamlib.MAX_ID)

    def list_clients(self):
        if self.init_forest() and self.forest.trees:
            t = self.forest.trees[-1]
            return [v
                     for k, v in t.lookup_range(self.minkey, self.maxkey)
                     if self.unkey(k)[2] == self.CLIENT_NAME]
        else:
            return []

    def find_client_id(self, t, client_name):
        minkey = self.key(client_name, 0, 0)
        maxkey = self.key(client_name, obnamlib.MAX_ID, self.SUBKEY_MAX)
        for k, v in t.lookup_range(minkey, maxkey):
            checksum, client_id, subkey = self.unkey(k)
            if subkey == self.CLIENT_NAME and v == client_name:
                return client_id
        return None

    def get_client_id(self, client_name):
        if not self.init_forest() or not self.forest.trees:
            return None
        t = self.forest.trees[-1]
        return self.find_client_id(t, client_name)

    def add_client(self, client_name):
        logging.info('Adding client %s' % client_name)
        self.start_changes()
        if self.find_client_id(self.tree, client_name) is None:
            while True:
                candidate_id = self.random_id()
                key = self.key(client_name, candidate_id, self.CLIENT_NAME)
                try:
                    self.tree.lookup(key)
                except KeyError:
                    break
            key = self.key(client_name, candidate_id, self.CLIENT_NAME)
            self.tree.insert(key, client_name)
            logging.debug('Client %s has id %s' % (client_name, candidate_id))

    def remove_client(self, client_name):
        logging.info('Removing client %s' % client_name)
        self.start_changes()
        client_id = self.find_client_id(self.tree, client_name)
        if client_id is not None:
            key = self.key(client_name, client_id, self.CLIENT_NAME)
            self.tree.remove(key)

    def get_client_keyid(self, client_name):
        if self.init_forest() and self.forest.trees:
            t = self.forest.trees[-1]
            client_id = self.find_client_id(t, client_name)
            if client_id is not None:
                key = self.key(client_name, client_id, self.KEYID)
                for k, v in t.lookup_range(key, key):
                    return v
        return None

    def set_client_keyid(self, client_name, keyid):
        logging.info('Setting client %s to use key %s' % (client_name, keyid))
        self.start_changes()
        client_id = self.find_client_id(self.tree, client_name)
        key = self.key(client_name, client_id, self.KEYID)
        if keyid is None:
            self.tree.remove_range(key, key)
        else:
            self.tree.insert(key, keyid)

