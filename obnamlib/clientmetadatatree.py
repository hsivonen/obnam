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


class ClientMetadataTree(obnamlib.StoreTree):

    '''Store per-client metadata about files.
    
    Actual file contents is stored elsewhere, this stores just the 
    metadata about files: names, inode info, and what chunks of
    data they use.
    
    See http://braawi.org/obnam/ondisk/ for a description of how
    this works.
    
    '''
    
    # Filesystem metadata.
    PREFIX_FS_META = 0      # prefix
    FILE_NAME = 0           # subkey type for storing pathnames
    FILE_CHUNKS = 1         # subkey type for list of chunks
    FILE_CHUNK_GROUPS = 2   # subkey type for list of chunk groups
    FILE_METADATA = 3       # subkey type for inode fields, etc
    DIR_CONTENTS = 4        # subkey type for list of directory contents
    
    FILE_METADATA_ENCODED = 0 # subkey value for encoded obnamlib.Metadata().
    
    # References to chunks in this generation.
    # Main key is the chunk id, subkey type is always 0, subkey is file id
    # for file that uses the chunk.
    PREFIX_CHUNK_REF = 1
    
    # Metadata about the generation. The main key is always the hash of
    # 'generation', subkey type field is always 0.
    PREFIX_GEN_META = 2     # prefix
    GEN_ID = 0              # subkey type for generation id
    GEN_STARTED = 1         # subkey type for when generation was started
    GEN_ENDED = 2           # subkey type for when generation was ended
    GEN_IS_CHECKPOINT = 3   # subkey type for whether generation is checkpoint
    
    # Maximum values for the subkey type field, and the subkey field.
    # Both have a minimum value of 0.

    TYPE_MAX = 255
    SUBKEY_MAX = struct.pack('!Q', 2**64-1)
    
    # Maximum value for file ids, client ids, chunk ids, chunk group ids.
    max_id = 2**64-1

    def __init__(self, fs, client_dir, node_size, upload_queue_size, lru_size):
        key_bytes = len(self.hashkey(0, self.hash_name(''), 0, 0))
        obnamlib.StoreTree.__init__(self, fs, client_dir, key_bytes, 
                                    node_size, upload_queue_size, lru_size)
        self.genhash = self.hash_name('generation')
        self.curgen = None
        self.known_generations = dict()

    def hash_name(self, filename):
        '''Return hash of filename suitable for use as main key.'''
        return hashlib.md5(filename).digest()[:8]

    def hashkey(self, prefix, mainhash, subtype, subkey):
        '''Compute a full key.

        The full key consists of three parts:

        * prefix (0 for filesystem metadata, 1 for chunk refs)
        * a hash of mainkey (64 bits)
        * the subkey type (8 bits)
        * type subkey (64 bits)

        These are catenated.

        mainhash must be a string of 8 bytes.

        subtype must be an integer in the range 0.255, inclusive.

        subkey must be either a string or an integer. If it is a string,
        it will be padded with NUL bytes at the end, if it is less than
        8 bytes, and truncated, if longer. If it is an integer, it will
        be converted as a string, and the value must fit into 64 bits.

        '''
        
        if type(subkey) == str:
            subkey = (subkey + '\0' * 8)[:8]
            fmt = '!B8sB8s'
        else:
            assert type(subkey) in [int, long]
            fmt = '!B8sBQ'

        return struct.pack(fmt, prefix, mainhash, subtype, subkey)

    def fskey(self, mainhash, subtype, subkey):
        ''''Generate key for filesystem metadata.'''
        return self.hashkey(self.PREFIX_FS_META, mainhash, subtype, subkey)

    def genkey(self, subkey):
        '''Generate key for generation metadata.'''
        return self.hashkey(self.PREFIX_GEN_META, self.genhash, 0, subkey)

    def int2bin(self, integer):
        '''Convert an integer to a binary string representation.'''
        return struct.pack('!Q', integer)

    def chunk_key(self, chunk_id, file_id):
        '''Generate a key for a chunk reference.'''
        return self.hashkey(self.PREFIX_CHUNK_REF, self.int2bin(chunk_id),
                            0, file_id)

    def get_file_id(self, gen, pathname):
        '''Return id for file in a given generation.'''
        
        # FIXME: This should handle hash collisions eventually.
        
        return self.hash_name(pathname)

    def _lookup_int(self, tree, key):
        return struct.unpack('!Q', tree.lookup(key))[0]

    def _insert_int(self, tree, key, value):
        return tree.insert(key, struct.pack('!Q', value))

    def commit(self, current_time=time.time):
        if self.forest:
            if self.curgen:
                now = int(current_time())
                self._insert_int(self.curgen, self.genkey(self.GEN_ENDED), now)
                self.curgen = None
            self.forest.commit()

    def find_generation(self, genid):
        if genid in self.known_generations:
            return self.known_generations[genid]

        if self.forest:
            key = self.genkey(self.GEN_ID)
            for t in self.forest.trees:
                if self._lookup_int(t, key) == genid:
                    self.known_generations[genid] = t
                    return t
        raise KeyError('Unknown generation %s' % genid)

    def list_generations(self):
        if self.forest:
            key = self.genkey(self.GEN_ID)
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
        self._insert_int(self.curgen, self.genkey(self.GEN_ID), gen_id)
        self._insert_int(self.curgen, self.genkey(self.GEN_STARTED), now)

    def set_current_generation_is_checkpoint(self, is_checkpoint):
        value = 1 if is_checkpoint else 0
        key = self.genkey(self.GEN_IS_CHECKPOINT)
        self._insert_int(self.curgen, key, value)

    def get_is_checkpoint(self, genid):
        tree = self.find_generation(genid)
        key = self.genkey(self.GEN_IS_CHECKPOINT)
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
        return self._lookup_int(tree, self.genkey(self.GEN_ID))

    def _lookup_time(self, tree, what):
        try:
            return self._lookup_int(tree, self.genkey(what))
        except KeyError:
            return None

    def get_generation_times(self, genid):
        tree = self.find_generation(genid)
        return (self._lookup_time(tree, self.GEN_STARTED),
                self._lookup_time(tree, self.GEN_ENDED))

    def _remove_filename_data(self, filename):
        file_id = self.get_file_id(self.curgen, filename)
        minkey = self.fskey(file_id, 0, 0)
        maxkey = self.fskey(file_id, self.TYPE_MAX, self.SUBKEY_MAX)
        self.curgen.remove_range(minkey, maxkey)

        # Also remove from parent's contents.
        parent = os.path.dirname(filename)
        if parent != filename: # root dir is its own parent
            parent_id = self.get_file_id(self.curgen, parent)
            key = self.fskey(parent_id, self.DIR_CONTENTS, file_id)
            # The range removal will work even if the key does not exist.
            self.curgen.remove_range(key, key)

    def create(self, filename, encoded_metadata):
        namehash = self.hash_name(filename)
        file_id = self.get_file_id(self.curgen, filename)
        key = self.fskey(namehash, self.FILE_NAME, file_id)
        try:
            old_metadata = self.curgen.lookup(key)
        except KeyError:
            old_metadata = None
        if encoded_metadata != old_metadata:
            self.set_metadata(filename, encoded_metadata)

        # Add to parent's contents, unless already there.
        parent = os.path.dirname(filename)
        if parent != filename: # root dir is its own parent
            basename = os.path.basename(filename)
            parent_id = self.get_file_id(self.curgen, parent)
            key = self.fskey(parent_id, self.DIR_CONTENTS, file_id)
            # We could just insert, but that would cause unnecessary
            # churn in the tree if nothing changes.
            try:
                self.curgen.lookup(key)
            except KeyError:
                self.curgen.insert(key, basename)

    def get_metadata(self, genid, filename):
        tree = self.find_generation(genid)
        file_id = self.get_file_id(tree, filename)
        key = self.fskey(file_id, self.FILE_METADATA, 
                         self.FILE_METADATA_ENCODED)
        return tree.lookup(key)

    def set_metadata(self, filename, encoded_metadata):
        namehash = self.hash_name(filename)
        file_id = self.get_file_id(self.curgen, filename)
        key1 = self.fskey(namehash, self.FILE_NAME, file_id)
        self.curgen.insert(key1, filename)
        
        key2 = self.fskey(file_id, self.FILE_METADATA, 
                          self.FILE_METADATA_ENCODED)
        self.curgen.insert(key2, encoded_metadata)

    def remove(self, filename):
        self._remove_filename_data(filename)

    def listdir(self, genid, dirname):
        tree = self.find_generation(genid)
        dir_id = self.get_file_id(tree, dirname)
        minkey = self.fskey(dir_id, self.DIR_CONTENTS, 0)
        maxkey = self.fskey(dir_id, self.DIR_CONTENTS, self.SUBKEY_MAX)
        basenames = []
        for key, value in tree.lookup_range(minkey, maxkey):
            basenames.append(value)
        return basenames

    def get_file_chunks(self, genid, filename):
        tree = self.find_generation(genid)
        file_id = self.get_file_id(tree, filename)
        minkey = self.fskey(file_id, self.FILE_CHUNKS, 0)
        maxkey = self.fskey(file_id, self.FILE_CHUNKS, self.SUBKEY_MAX)
        pairs = tree.lookup_range(minkey, maxkey)
        return [struct.unpack('!Q', value)[0]
                for key, value in pairs]
    
    def set_file_chunks(self, filename, chunkids):
        file_id = self.get_file_id(self.curgen, filename)
        minkey = self.fskey(file_id, self.FILE_CHUNKS, 0)
        maxkey = self.fskey(file_id, self.FILE_CHUNKS, self.SUBKEY_MAX)
        self.curgen.remove_range(minkey, maxkey)
        for i, chunkid in enumerate(chunkids):
            key = self.fskey(file_id, self.FILE_CHUNKS, i)
            self.curgen.insert(key, struct.pack('!Q', chunkid))
        
    def get_file_chunk_groups(self, genid, filename):
        tree = self.find_generation(genid)
        file_id = self.get_file_id(tree, filename)
        minkey = self.fskey(file_id, self.FILE_CHUNK_GROUPS, 0)
        maxkey = self.fskey(file_id, self.FILE_CHUNK_GROUPS, self.SUBKEY_MAX)
        return [struct.unpack('!Q', value)[0]
                for key, value in tree.lookup_range(minkey, maxkey)]

    def set_file_chunk_groups(self, filename, cgids):
        file_id = self.get_file_id(self.curgen, filename)
        minkey = self.fskey(file_id, self.FILE_CHUNK_GROUPS, 0)
        maxkey = self.fskey(file_id, self.FILE_CHUNK_GROUPS, self.SUBKEY_MAX)
        self.curgen.remove_range(minkey, maxkey)
        for i, cgid in enumerate(cgids):
            key = self.fskey(file_id, self.FILE_CHUNK_GROUPS, i)
            self.curgen.insert(key, struct.pack('!Q', cgid))

