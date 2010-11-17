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
import os
import struct
import time

import obnamlib


class GenerationStore(obnamlib.StoreTree):

    '''Store generations.

    We store things in the B-tree forest as follows:

    * each generation is a tree; each tree is a generation
    * tree key is constructed from three parts: a main key, a subkey type,
      and the subkey itself
      * the main key is a hash of a string, and is 64 bits
      * the subkey type is 8 bits
      * the subkey is a string and is 64 bits
    * the string for the main key is either a fully qualified pathname, 
      for filesystem objects, or the string "generation" for generation
      metadata
    * a filesystem object's metadata (inode data, etc) is stored as a blob,
      in a specific subkey
    * a regular file's contents are stored using chunks, which are stored
      outside of the tree
      * each chunk has an id
      * the chunk ids are stored in the tree, using a dedicated subkey type,
        with the subkey being the ordinal for each subkey: 0, 1, 2, ...
    * a directory's contents are stored by storing the main key (the hash,
      not the input to the hash function) for each filesystem object in the
      directory
      * similar to chunks in files
      * dedicated subkey type
      * subkey is hash of directory entry's full pathname

    '''

    TYPE_MAX = 255
    SUBKEY_MAX = struct.pack('!Q', 2**64-1)

    # Subkey types.

    GEN_META = 0
    FILE = 1
    FILE_CHUNKS = 2
    FILE_CHUNK_GROUPS = 3
    DIR_CONTENTS = 4

    # Subkey values when they are fixed.

    GEN_META_ID = 0
    GEN_META_STARTED = 1
    GEN_META_ENDED = 2
    GEN_META_IS_CHECKPOINT = 3

    FILE_NAME = 0
    FILE_METADATA = 1
    
    def __init__(self, fs, client_id, node_size, upload_queue_size, lru_size):
        key_bytes = len(self.key('', 0, 0))
        obnamlib.StoreTree.__init__(self, fs, client_id, key_bytes, node_size,
                                    upload_queue_size, lru_size)
        self.curgen = None
        self.known_generations = dict()

    def hash_name(self, filename):
        '''Return hash of filename suitable for use as main key.'''
        return hashlib.md5(filename).digest()[:8]

    def hashkey(self, mainhash, subtype, subkey):
        '''Like key, but main key's hash is given.'''
        
        if type(subkey) == int:
            fmt = '!8sBQ'
        else:
            assert type(subkey) == str
            subkey = (subkey + '\0' * 8)[:8]
            fmt = '!8sB8s'

        return struct.pack(fmt, mainhash, subtype, subkey)

    def key(self, mainkey, subtype, subkey):
        '''Compute a full key.

        The full key consists of three parts:

        * a hash of mainkey (64 bits)
        * the subkey type (8 bits)
        * type subkey (64 bits)

        These are catenated.

        mainkey must be a string.

        subtype must be an integer in the range 0.255, inclusive.

        subkey must be either a string or an integer. If it is a string,
        it will be padded with NUL bytes at the end, if it is less than
        8 bytes, and truncated, if longer. If it is an integer, it will
        be converted as a string, and the value must fit into 64 bits.

        '''

        return self.hashkey(self.hash_name(mainkey), subtype, subkey)

    def genkey(self, subkey):
        '''Generate key for generation metadata.'''
        return self.key('generation', self.GEN_META, subkey)

    def _lookup_int(self, tree, key):
        return struct.unpack('!Q', tree.lookup(key))[0]

    def _insert_int(self, tree, key, value):
        return tree.insert(key, struct.pack('!Q', value))

    def commit(self):
        if self.forest:
            if self.curgen:
                now = int(time.time())
                self._insert_int(self.curgen, 
                                 self.genkey(self.GEN_META_ENDED), 
                                 now)
                self.curgen = None
            self.forest.commit()

    def find_generation(self, genid):
        if genid in self.known_generations:
            return self.known_generations[genid]

        key = self.genkey(self.GEN_META_ID)
        for t in self.forest.trees:
            if self._lookup_int(t, key) == genid:
                self.known_generations[genid] = t
                return t
        raise KeyError('Unknown generation %s' % genid)

    def list_generations(self):
        if self.forest:
            key = self.genkey(self.GEN_META_ID)
            return [self._lookup_int(t, key) for t in self.forest.trees]
        else:
            return []

    def start_generation(self, current_time=time.time):
        assert self.curgen is None
        if self.forest.trees:
            old = self.forest.trees[-1]
        else:
            old = None
        self.curgen = self.forest.new_tree(old=old)
        gen_id = self.forest.new_id()
        now = int(current_time())
        self._insert_int(self.curgen, self.genkey(self.GEN_META_ID), gen_id)
        self._insert_int(self.curgen, self.genkey(self.GEN_META_STARTED), now)

    def set_current_generation_is_checkpoint(self, is_checkpoint):
        value = 1 if is_checkpoint else 0
        key = self.genkey(self.GEN_META_IS_CHECKPOINT)
        self._insert_int(self.curgen, key, value)

    def get_is_checkpoint(self, genid):
        tree = self.find_generation(genid)
        key = self.genkey(self.GEN_META_IS_CHECKPOINT)
        try:
            return self._lookup_int(tree, key)
        except KeyError:
            return 0

    def remove_generation(self, genid):
        tree = self.find_generation(genid)
        if tree == self.curgen:
            self.curgen = None
        self.forest.remove_tree(tree)

    def get_generation_id(self, tree):
        return self._lookup_int(tree, self.genkey(self.GEN_META_ID))

    def _lookup_time(self, tree, what):
        try:
            return self._lookup_int(tree, self.genkey(what))
        except KeyError:
            return None

    def get_generation_times(self, genid):
        tree = self.find_generation(genid)
        return (self._lookup_time(tree, self.GEN_META_STARTED),
                self._lookup_time(tree, self.GEN_META_ENDED))

    def _remove_filename_data(self, filename):
        minkey = self.key(filename, 0, 0)
        maxkey = self.key(filename, self.TYPE_MAX, self.SUBKEY_MAX)
        self.curgen.remove_range(minkey, maxkey)

        # Also remove from parent's contents.
        parent = os.path.dirname(filename)
        if parent != filename: # root dir is its own parent
            subkey = self.hash_name(filename)
            key = self.key(parent, self.DIR_CONTENTS, subkey)
            self.curgen.remove_range(key, key)

    def create(self, filename, metadata):
        key = self.key(filename, self.FILE, self.FILE_METADATA)
        try:
            old_metadata = self.curgen.lookup(key)
        except KeyError:
            old_metadata = None
        if metadata != old_metadata:
            self.set_metadata(filename, metadata)

        # Add to parent's contents, unless already there.
        parent = os.path.dirname(filename)
        if parent != filename: # root dir is its own parent
            basename = os.path.basename(filename)
            subkey = self.hash_name(filename)
            key = self.key(parent, self.DIR_CONTENTS, subkey)
            # We could just insert, but that would cause unnecessary
            # churn in the tree if nothing changes.
            try:
                self.curgen.lookup(key)
            except KeyError:
                self.curgen.insert(key, basename)

    def get_metadata(self, genid, filename):
        tree = self.find_generation(genid)
        return tree.lookup(self.key(filename, self.FILE, self.FILE_METADATA))

    def set_metadata(self, filename, encoded_metadata):
        self.curgen.insert(self.key(filename, self.FILE, self.FILE_NAME),
                           filename)
        self.curgen.insert(self.key(filename, self.FILE, self.FILE_METADATA),
                           encoded_metadata)

    def remove(self, filename):
        self._remove_filename_data(filename)

    def listdir(self, genid, dirname):
        tree = self.find_generation(genid)
        minkey = self.key(dirname, self.DIR_CONTENTS, 0)
        maxkey = self.key(dirname, self.DIR_CONTENTS, self.SUBKEY_MAX)
        basenames = []
        for key, value in tree.lookup_range(minkey, maxkey):
            basenames.append(value)
        return basenames

    def get_file_chunks(self, genid, filename):
        tree = self.find_generation(genid)
        minkey = self.key(filename, self.FILE_CHUNKS, 0)
        maxkey = self.key(filename, self.FILE_CHUNKS, self.SUBKEY_MAX)
        pairs = tree.lookup_range(minkey, maxkey)
        return [struct.unpack('!Q', value)[0]
                for key, value in pairs]
    
    def set_file_chunks(self, filename, chunkids):
        minkey = self.key(filename, self.FILE_CHUNKS, 0)
        maxkey = self.key(filename, self.FILE_CHUNKS, self.SUBKEY_MAX)
        self.curgen.remove_range(minkey, maxkey)
        for i, chunkid in enumerate(chunkids):
            self.curgen.insert(self.key(filename, self.FILE_CHUNKS, i),
                               struct.pack('!Q', chunkid))
        
    def get_file_chunk_groups(self, genid, filename):
        tree = self.find_generation(genid)
        minkey = self.key(filename, self.FILE_CHUNK_GROUPS, 0)
        maxkey = self.key(filename, self.FILE_CHUNK_GROUPS, self.SUBKEY_MAX)
        return [struct.unpack('!Q', value)[0]
                for key, value in tree.lookup_range(minkey, maxkey)]

    def set_file_chunk_groups(self, filename, cgids):
        minkey = self.key(filename, self.FILE_CHUNK_GROUPS, 0)
        maxkey = self.key(filename, self.FILE_CHUNK_GROUPS, self.SUBKEY_MAX)
        self.curgen.remove_range(minkey, maxkey)
        for i, cgid in enumerate(cgids):
            self.curgen.insert(self.key(filename, self.FILE_CHUNK_GROUPS, i),
                               struct.pack('!Q', cgid))

