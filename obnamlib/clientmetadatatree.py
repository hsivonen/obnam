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
import os
import struct
import time
import tracing

import obnamlib


class ClientMetadataTree(obnamlib.RepositoryTree):

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
    GEN_FILE_COUNT = 4      # subkey type for count of files+dirs in generation
    GEN_TOTAL_DATA = 5      # subkey type for sum of all file sizes in gen
    
    # Maximum values for the subkey type field, and the subkey field.
    # Both have a minimum value of 0.

    TYPE_MAX = 255
    SUBKEY_MAX = struct.pack('!Q', obnamlib.MAX_ID)
    
    def __init__(self, fs, client_dir, node_size, upload_queue_size, lru_size,
                 hooks):
        tracing.trace('new ClientMetadataTree, client_dir=%s' % client_dir)
        key_bytes = len(self.hashkey(0, self.hash_name(''), 0, 0))
        obnamlib.RepositoryTree.__init__(self, fs, client_dir, key_bytes, 
                                         node_size, upload_queue_size, 
                                         lru_size, hooks)
        self.genhash = self.hash_name('generation')
        self.known_generations = dict()
        self.chunkids_per_key = max(1,
                                    int(node_size / 4 / struct.calcsize('Q')))

    def hash_name(self, filename):
        '''Return hash of filename suitable for use as main key.'''
        tracing.trace(repr(filename))
        def hash(s):
            return hashlib.md5(s).digest()[:4]
        dirname = os.path.dirname(filename)
        basename = os.path.basename(filename)
        return hash(dirname) + hash(basename)

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

    def chunk_unkey(self, key):
        '''Return the chunk and file ids in a chunk key.'''
        parts = struct.unpack('!BQBQ', key)
        return parts[1], parts[3]

    def get_file_id(self, gen, pathname):
        '''Return id for file in a given generation.'''
        
        # FIXME: This should handle hash collisions eventually.
        
        return self.hash_name(pathname)

    def _lookup_int(self, tree, key):
        return struct.unpack('!Q', tree.lookup(key))[0]

    def _insert_int(self, tree, key, value):
        return tree.insert(key, struct.pack('!Q', value))

    def commit(self, current_time=time.time):
        tracing.trace('committing ClientMetadataTree')
        if self.tree:
            now = int(current_time())
            self._insert_int(self.tree, self.genkey(self.GEN_ENDED), now)
            genid = self.get_generation_id(self.tree)
            self._insert_count(genid, self.GEN_FILE_COUNT, self.file_count)
            self._insert_count(genid, self.GEN_TOTAL_DATA, self.total_data)
        obnamlib.RepositoryTree.commit(self)

    def find_generation(self, genid):
        if genid in self.known_generations:
            return self.known_generations[genid]

        if self.forest:
            key = self.genkey(self.GEN_ID)
            for t in self.forest.trees:
                t_genid = self._lookup_int(t, key)
                self.known_generations[t_genid] = t
                if t_genid == genid:
                    return t
        raise KeyError('Unknown generation %s' % genid)

    def list_generations(self):
        if self.forest:
            key = self.genkey(self.GEN_ID)
            return [self._lookup_int(t, key) for t in self.forest.trees]
        else:
            return []

    def start_generation(self, current_time=time.time):
        tracing.trace('start new generation')
        self.start_changes()
        gen_id = self.forest.new_id()
        now = int(current_time())
        self._insert_int(self.tree, self.genkey(self.GEN_ID), gen_id)
        self._insert_int(self.tree, self.genkey(self.GEN_STARTED), now)
        self.file_count = self.get_generation_files(gen_id)
        self.total_data = self.get_generation_data(gen_id)

    def set_current_generation_is_checkpoint(self, is_checkpoint):
        tracing.trace('is_checkpoint=%s', is_checkpoint)
        value = 1 if is_checkpoint else 0
        key = self.genkey(self.GEN_IS_CHECKPOINT)
        self._insert_int(self.tree, key, value)

    def get_is_checkpoint(self, genid):
        tree = self.find_generation(genid)
        key = self.genkey(self.GEN_IS_CHECKPOINT)
        try:
            return self._lookup_int(tree, key)
        except KeyError:
            return 0

    def remove_generation(self, genid):
        tracing.trace('genid=%s', genid)
        tree = self.find_generation(genid)
        if tree == self.tree:
            self.tree = None
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

    def get_generation_files(self, genid):
        return self._lookup_count(genid, self.GEN_FILE_COUNT)

    def get_generation_data(self, genid):
        return self._lookup_count(genid, self.GEN_TOTAL_DATA)

    def _lookup_count(self, genid, count_type):
        tree = self.find_generation(genid)
        key = self.genkey(count_type)
        try:
            return self._lookup_int(tree, key)
        except KeyError:
            return 0

    def _insert_count(self, genid, count_type, count):
        tree = self.find_generation(genid)
        key = self.genkey(count_type)
        return self._insert_int(tree, key, count)

    def get_generation_file_count(self, genid):
        return self._lookup_count(genid, self.GEN_FILE_COUNT)

    def create(self, filename, encoded_metadata):
        tracing.trace('filename=%s', filename)
        file_id = self.get_file_id(self.tree, filename)
        gen_id = self.get_generation_id(self.tree)
        try:
            old_metadata = self.get_metadata(gen_id, filename)
        except KeyError:
            old_metadata = None
            self.file_count += 1
        else:
            old = obnamlib.decode_metadata(old_metadata)
            if old.isfile():
                self.total_data -= old.st_size or 0

        metadata = obnamlib.decode_metadata(encoded_metadata)
        if metadata.isfile():
            self.total_data += metadata.st_size or 0

        if encoded_metadata != old_metadata:
            tracing.trace('new or changed metadata')
            self.set_metadata(filename, encoded_metadata)

        # Add to parent's contents, unless already there.
        parent = os.path.dirname(filename)
        tracing.trace('parent=%s', parent)
        if parent != filename: # root dir is its own parent
            basename = os.path.basename(filename)
            parent_id = self.get_file_id(self.tree, parent)
            key = self.fskey(parent_id, self.DIR_CONTENTS, file_id)
            # We could just insert, but that would cause unnecessary
            # churn in the tree if nothing changes.
            try:
                self.tree.lookup(key)
                tracing.trace('was already in parent') # pragma: no cover
            except KeyError:
                self.tree.insert(key, basename)
                tracing.trace('added to parent')

    def get_metadata(self, genid, filename):
        tree = self.find_generation(genid)
        file_id = self.get_file_id(tree, filename)
        key = self.fskey(file_id, self.FILE_METADATA, 
                         self.FILE_METADATA_ENCODED)
        return tree.lookup(key)

    def set_metadata(self, filename, encoded_metadata):
        tracing.trace('filename=%s', filename)

        file_id = self.get_file_id(self.tree, filename)
        key1 = self.fskey(file_id, self.FILE_NAME, file_id)
        self.tree.insert(key1, filename)
        
        key2 = self.fskey(file_id, self.FILE_METADATA, 
                          self.FILE_METADATA_ENCODED)
        self.tree.insert(key2, encoded_metadata)

    def remove(self, filename):
        tracing.trace('filename=%s', filename)

        file_id = self.get_file_id(self.tree, filename)
        genid = self.get_generation_id(self.tree)
        self.file_count -= 1
        
        try:
            encoded_metadata = self.get_metadata(genid, filename)
        except KeyError:
            pass
        else:
            metadata = obnamlib.decode_metadata(encoded_metadata)
            if metadata.isfile():
                self.total_data -= metadata.st_size or 0

        # Remove any children.
        minkey = self.fskey(file_id, self.DIR_CONTENTS, 0)
        maxkey = self.fskey(file_id, self.DIR_CONTENTS, obnamlib.MAX_ID)
        for key, basename in self.tree.lookup_range(minkey, maxkey):
            self.remove(os.path.join(filename, basename))

        # Remove chunk refs.
        for chunkid in self.get_file_chunks(genid, filename):
            key = self.chunk_key(chunkid, file_id)
            self.tree.remove_range(key, key)
            
        # Remove this file's metadata.
        minkey = self.fskey(file_id, 0, 0)
        maxkey = self.fskey(file_id, self.TYPE_MAX, self.SUBKEY_MAX)
        self.tree.remove_range(minkey, maxkey)

        # Also remove from parent's contents.
        parent = os.path.dirname(filename)
        if parent != filename: # root dir is its own parent
            parent_id = self.get_file_id(self.tree, parent)
            key = self.fskey(parent_id, self.DIR_CONTENTS, file_id)
            # The range removal will work even if the key does not exist.
            self.tree.remove_range(key, key)
            
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
        chunkids = []
        for key, value in pairs:
            chunkids.extend(self._decode_chunks(value))
        return chunkids

    def _encode_chunks(self, chunkids):
        fmt = '!' + ('Q' * len(chunkids))
        return struct.pack(fmt, *chunkids)

    def _decode_chunks(self, encoded):
        size = struct.calcsize('Q')
        count = len(encoded) / size
        fmt = '!' + ('Q' * count)
        return struct.unpack(fmt, encoded)

    def _insert_chunks(self, tree, file_id, i, chunkids):
        key = self.fskey(file_id, self.FILE_CHUNKS, i)
        encoded = self._encode_chunks(chunkids)
        tree.insert(key, encoded)

    def set_file_chunks(self, filename, chunkids):
        tracing.trace('filename=%s', filename)
        tracing.trace('chunkids=%s', repr(chunkids))
    
        file_id = self.get_file_id(self.tree, filename)
        minkey = self.fskey(file_id, self.FILE_CHUNKS, 0)
        maxkey = self.fskey(file_id, self.FILE_CHUNKS, self.SUBKEY_MAX)

        for key, value in self.tree.lookup_range(minkey, maxkey):
            for chunkid in self._decode_chunks(value):
                k = self.chunk_key(chunkid, file_id)
                self.tree.remove_range(k, k)

        self.tree.remove_range(minkey, maxkey)

        self.append_file_chunks(filename, chunkids)

    def append_file_chunks(self, filename, chunkids):
        tracing.trace('filename=%s', filename)
        tracing.trace('chunkids=%s', repr(chunkids))

        file_id = self.get_file_id(self.tree, filename)

        minkey = self.fskey(file_id, self.FILE_CHUNKS, 0)
        maxkey = self.fskey(file_id, self.FILE_CHUNKS, self.SUBKEY_MAX)
        i = self.tree.count_range(minkey, maxkey)

        while chunkids:
            some = chunkids[:self.chunkids_per_key]
            self._insert_chunks(self.tree, file_id, i, some)
            for chunkid in some:
                self.tree.insert(self.chunk_key(chunkid, file_id), '')
            i += 1
            chunkids = chunkids[self.chunkids_per_key:]

    def chunk_in_use(self, gen_id, chunk_id):
        '''Is a chunk used by a generation?'''
        
        minkey = self.chunk_key(chunk_id, 0)
        maxkey = self.chunk_key(chunk_id, obnamlib.MAX_ID)
        t = self.find_generation(gen_id)
        return not t.range_is_empty(minkey, maxkey)

    def list_chunks_in_generation(self, gen_id):
        '''Return list of chunk ids used in a given generation.'''
        
        minkey = self.chunk_key(0, 0)
        maxkey = self.chunk_key(obnamlib.MAX_ID, obnamlib.MAX_ID)
        t = self.find_generation(gen_id)
        return list(set(self.chunk_unkey(key)[0]
                        for key, value in t.lookup_range(minkey, maxkey)))

