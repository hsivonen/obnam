# Copyright (C) 2009, 2010  Lars Wirzenius
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


import btree
import errno
import hashlib
import os
import random
import struct
import time

import obnamlib


class LockFail(Exception):

    pass


def require_root_lock(method):
    '''Decorator for ensuring the store's root node is locked.'''
    
    def helper(self, *args, **kwargs):
        if not self.got_root_lock:
            raise LockFail('have not got lock on root node')
        return method(self, *args, **kwargs)
    
    return helper


def require_client_lock(method):
    '''Decorator for ensuring the currently open client is locked by us.'''
    
    def helper(self, *args, **kwargs):
        if not self.got_client_lock:
            raise LockFail('have not got lock on client')
        return method(self, *args, **kwargs)
    
    return helper


def require_open_client(method):
    '''Decorator for ensuring store has an open client.
    
    client may be read/write (locked) or read-only.
    
    '''
    
    def helper(self, *args, **kwargs):
        if self.current_client is None:
            raise obnamlib.Error('client is not open')
        return method(self, *args, **kwargs)
    
    return helper


def require_started_generation(method):
    '''Decorator for ensuring a new generation has been started. '''
    
    def helper(self, *args, **kwargs):
        if self.new_generation is None:
            raise obnamlib.Error('new generation has not started')
        return method(self, *args, **kwargs)
    
    return helper


numeric_fields = [x for x in obnamlib.metadata_fields if x.startswith('st_')]
string_fields = [x for x in obnamlib.metadata_fields 
                 if x not in numeric_fields]
all_fields = numeric_fields + string_fields
num_numeric = len(numeric_fields)
metadata_format = struct.Struct('!Q' + 'Q' * len(obnamlib.metadata_fields))


def encode_metadata(metadata):
    flags = 0
    for i, name in enumerate(obnamlib.metadata_fields):
        if getattr(metadata, name) is not None:
            flags |= (1 << i)
    fields = ([flags] +
              [getattr(metadata, x) or 0 for x in numeric_fields] +
              [len(getattr(metadata, x) or '') for x in string_fields])
    string = ''.join(getattr(metadata, x) or '' for x in string_fields)
    return metadata_format.pack(*fields) + string
    

def flagtonone(flags, values):
    for i, value in enumerate(values):
        if flags & (1 << i):
            yield value
        else:
            yield None


def decode_metadata(encoded):
    buf = buffer(encoded)
    items = metadata_format.unpack_from(buf)

    flags = items[0]
    values = list(items[1:len(numeric_fields)+1])
    lengths = items[len(numeric_fields)+1:]
    
    offset = metadata_format.size
    append = values.append
    for length in lengths:
        append(encoded[offset:offset + length])
        offset += length

    args = dict(zip(all_fields, flagtonone(flags, values)))
    return obnamlib.Metadata(**args)


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
        if genid in self.known_generations: # pragma: no cover
            return self.known_generations[genid]

        key = self.genkey(self.GEN_META_ID)
        for t in self.forest.trees:
            if self._lookup_int(t, key) == genid:
                self.known_generations[genid] = t
                return t
        raise KeyError('Unknown generation %s' % genid) # pragma: no cover

    def list_generations(self):
        if self.forest:
            key = self.genkey(self.GEN_META_ID)
            return [self._lookup_int(t, key) for t in self.forest.trees]
        else:
            return []

    def start_generation(self):
        assert self.curgen is None
        if self.forest.trees:
            old = self.forest.trees[-1]
        else:
            old = None
        self.curgen = self.forest.new_tree(old=old)
        gen_id = self.forest.new_id()
        now = int(time.time())
        self._insert_int(self.curgen, self.genkey(self.GEN_META_ID), gen_id)
        self._insert_int(self.curgen, self.genkey(self.GEN_META_STARTED), now)

    def set_current_generation_is_checkpoint(self, is_checkpoint):
        value = 1 if is_checkpoint else 0
        key = self.genkey(self.GEN_META_IS_CHECKPOINT)
        self._insert_int(self.curgen, key, value)

    def get_is_checkpoint(self, genid):
        tree = self.find_generation(genid)
        key = self.genkey(self.GEN_META_IS_CHECKPOINT)
        return self._lookup_int(tree, key)

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


class Store(object):

    '''Store backup data.
    
    Backup data is stored on a virtual file system
    (obnamlib.VirtualFileSystem instance), in some form that
    the API of this class does not care about.
    
    The store may contain data for several clients that share 
    encryption keys. Each client is identified by a name.
    
    The store has a "root" object, which is conceptually a list of
    client names.
    
    Each client in turn is conceptually a list of generations,
    which correspond to snapshots of the user data that existed
    when the generation was created.
    
    Read-only access to the store does not require locking.
    Write access may affect only the root object, or only a client's
    own data, and thus locking may affect only the root, or only
    the client.
    
    When a new generation is started, it is a copy-on-write clone
    of the previous generation, and the caller needs to modify
    the new generation to match the current state of user data.

    '''

    def __init__(self, fs, node_size, upload_queue_size, lru_size):
        self.fs = fs
        self.node_size = node_size
        self.upload_queue_size = upload_queue_size
        self.lru_size = lru_size
        self.got_root_lock = False
        self.clientlist = obnamlib.ClientList(fs, node_size, upload_queue_size, 
                                              lru_size)
        self.got_client_lock = False
        self.client_lockfile = None
        self.current_client = None
        self.new_generation = None
        self.added_clients = []
        self.removed_clients = []
        self.removed_generations = []
        self.genstore = None
        self.chunksums = obnamlib.ChecksumTree(fs, 'chunksums', 
                                               len(self.checksum('')),
                                               node_size, upload_queue_size, 
                                               lru_size)
        self.groupsums = obnamlib.ChecksumTree(fs, 'groupsums', 
                                               len(self.checksum('')),
                                               node_size, upload_queue_size, 
                                               lru_size)
        self.chunkgroups = ChunkGroupTree(fs, node_size, upload_queue_size,
                                          lru_size)
        self.prev_chunkid = None

    def checksum(self, data):
        '''Return checksum of data.
        
        The checksum is (currently) MD5.
        
        Return a non-binary string (hexdigest) form of the checksum
        so that it can easily be used for filenames, or printed to
        log files, or whatever.
        
        '''

        checksummer = self.new_checksummer()
        checksummer.update(data)
        return checksummer.hexdigest()

    def new_checksummer(self):
        '''Return a new checksum algorithm.'''
        return hashlib.md5()

    def list_clients(self):
        '''Return list of names of clients using this store.'''

        listed = set(self.clientlist.list_clients())
        added = set(self.added_clients)
        removed = set(self.removed_clients)
        clients = listed.union(added).difference(removed)
        return list(clients)

    def lock_root(self):
        '''Lock root node.
        
        Raise obnamlib.LockFail if locking fails. Lock will be released
        by commit_root() or unlock_root().
        
        '''
        
        try:
            self.fs.write_file('root.lock', '')
        except OSError, e:
            if e.errno == errno.EEXIST:
                raise LockFail('Lock file root.lock already exists')
        self.got_root_lock = True
        self.added_clients = []
        self.removed_clients = []

    @require_root_lock
    def unlock_root(self):
        '''Unlock root node without committing changes made.'''
        self.added_clients = []
        self.removed_clients = []
        self.fs.remove('root.lock')
        self.got_root_lock = False
        
    @require_root_lock
    def commit_root(self):
        '''Commit changes to root node, and unlock it.'''
        for client_name in self.added_clients:
            self.clientlist.add_client(client_name)
        self.added_clients = []
        for client_name in self.removed_clients:
            client_id = self.clientlist.get_client_id(client_name)
            if client_id is not None and self.fs.exists(client_id):
                self.fs.rmtree(client_id)
            self.clientlist.remove_client(client_name)
        self.clientlist.commit()
        self.unlock_root()
        
    @require_root_lock
    def add_client(self, client_name):
        '''Add a new client to the store.'''
        if client_name in self.list_clients():
            raise obnamlib.Error('client %s already exists in store' % 
                                 client_name)
        self.added_clients.append(client_name)
        
    @require_root_lock
    def remove_client(self, client_name):
        '''Remove a client from the store.
        
        This removes all data related to the client, including all
        actual file data unless other clients also use it.
        
        '''
        
        if client_name not in self.list_clients():
            raise obnamlib.Error('client %s does not exist' % client_name)
        self.removed_clients.append(client_name)
        
    def lock_client(self, client_name):
        '''Lock a client for exclusive write access.
        
        Raise obnamlib.LockFail if locking fails. Lock will be released
        by commit_client() or unlock_client().

        '''

        client_id = self.clientlist.get_client_id(client_name)
        if client_id is None:
            raise LockFail('client %s does not exit' % client_name)
        
        lockname = os.path.join(client_id, 'lock')
        try:
            self.fs.write_file(lockname, '')
        except OSError, e:
            if e.errno == errno.EEXIST:
                raise LockFail('client %s is already locked' % client_name)
        self.got_client_lock = True
        self.client_lockfile = lockname
        self.current_client = client_name
        self.added_generations = []
        self.removed_generations = []
        self.genstore = GenerationStore(self.fs, client_id, self.node_size, 
                                        self.upload_queue_size, self.lru_size)
        self.genstore.require_forest()

    @require_client_lock
    def unlock_client(self):
        '''Unlock currently locked client, without committing changes.'''
        self.new_generation = None
        for genid in self.added_generations:
            self._really_remove_generation(genid)
        self.genstore = None # FIXME: This should remove uncommitted data.
        self.added_generations = []
        self.removed_generations = []
        self.fs.remove(self.client_lockfile)
        self.client_lockfile = None
        self.got_client_lock = False
        self.current_client = None

    @require_client_lock
    def commit_client(self, checkpoint=False):
        '''Commit changes to and unlock currently locked client.'''
        if self.new_generation:
            self.genstore.set_current_generation_is_checkpoint(checkpoint)
        self.added_generations = []
        for genid in self.removed_generations:
            self._really_remove_generation(genid)
        self.genstore.commit()
        self.chunksums.commit()
        self.groupsums.commit()
        self.chunkgroups.commit()
        self.unlock_client()
        
    def open_client(self, client_name):
        '''Open a client for read-only operation.'''
        client_id = self.clientlist.get_client_id(client_name)
        if client_id is None:
            raise obnamlib.Error('%s is not an existing client' % client_name)
        self.current_client = client_name
        self.genstore = GenerationStore(self.fs, client_id, self.node_size,
                                        self.upload_queue_size, self.lru_size)
        self.genstore.init_forest()
        
    @require_open_client
    def list_generations(self):
        '''List existing generations for currently open client.'''
        return self.genstore.list_generations()
        
    @require_open_client
    def get_is_checkpoint(self, genid):
        '''Is a generation a checkpoint one?'''
        return self.genstore.get_is_checkpoint(genid)
        
    @require_client_lock
    def start_generation(self):
        '''Start a new generation.
        
        The new generation is a copy-on-write clone of the previous
        one (or empty, if first generation).
        
        '''
        if self.new_generation is not None:
            raise obnamlib.Error('Cannot start two new generations')
        self.genstore.require_forest()
        self.genstore.start_generation()
        self.new_generation = \
            self.genstore.get_generation_id(self.genstore.curgen)
        self.added_generations.append(self.new_generation)
        return self.new_generation

    @require_client_lock
    def _really_remove_generation(self, gen):
        '''Really remove a committed generation.
        
        This is not part of the public API.
        
        This does not make any safety checks.
        
        '''

        self.genstore.remove_generation(gen)

    @require_client_lock
    def remove_generation(self, gen):
        '''Remove a committed generation.'''
        if gen == self.new_generation:
            raise obnamlib.Error('cannot remove started generation')
        self.removed_generations.append(gen)

    @require_open_client
    def get_generation_times(self, gen):
        '''Return start and end times of a generation.
        
        An unfinished generation has no end time, so None is returned.
        
        '''

        return self.genstore.get_generation_times(gen)

    @require_open_client
    def listdir(self, gen, dirname):
        '''Return list of basenames in a directory within generation.'''
        return self.genstore.listdir(gen, dirname)
        
    @require_open_client
    def get_metadata(self, gen, filename):
        '''Return metadata for a file in a generation.'''

        try:
            encoded = self.genstore.get_metadata(gen, filename)
        except KeyError:
            raise obnamlib.Error('%s does not exist' % filename)
        return decode_metadata(encoded)

    @require_started_generation
    def create(self, filename, metadata):
        '''Create a new (empty) file in the new generation.'''
        encoded = encode_metadata(metadata)
        self.genstore.create(filename, encoded)

    @require_started_generation
    def remove(self, filename):
        '''Remove file or directory or directory tree from generation.'''
        self.genstore.remove(filename)

    def _chunk_filename(self, chunkid):
        basename = '%x' % chunkid
        subdir = '%d' % (chunkid / (2**13))
        return os.path.join('chunks', subdir, basename)

    @require_started_generation
    def put_chunk(self, data, checksum):
        '''Put chunk of data into store.
        
        checksum is the checksum of the data, and must be the same
        value as returned by self.checksum(data). However, since all
        known use cases require the caller to know the checksum before
        calling this method, and since computing checksums is
        expensive, we micro-optimize a little bit by passing it as
        an argument.
        
        If the same data is already in the store, it will be put there
        a second time. It is the caller's responsibility to check
        that the data is not already in the store.
        
        Return the unique identifier of the new chunk.
        
        '''
        
        max_chunkid = 2**64 - 1
        def random_chunkid():
            return random.randint(0, max_chunkid)
        
        if self.prev_chunkid is None:
            self.prev_chunkid = random_chunkid()
        while True:
            chunkid = (self.prev_chunkid + 1) % max_chunkid
            filename = self._chunk_filename(chunkid)
            if not self.fs.exists(filename):
                break
            self.prev_chunkid = random_chunkid() # pragma: no cover
        self.prev_chunkid = chunkid
        dirname = os.path.dirname(filename)
        if not self.fs.exists(dirname):
            self.fs.makedirs(dirname)
        self.fs.write_file(filename, data)
        self.chunksums.add(self.checksum(data), chunkid)
        return chunkid
        
    @require_open_client
    def get_chunk(self, chunkid):
        '''Return data of chunk with given id.'''
        return self.fs.cat(self._chunk_filename(chunkid))
        
    @require_open_client
    def chunk_exists(self, chunkid):
        '''Does a chunk exist in the store?'''
        return self.fs.exists(self._chunk_filename(chunkid))
        
    @require_open_client
    def find_chunks(self, checksum):
        '''Return identifiers of chunks with given checksum.
        
        Because of hash collisions, the list may be longer than one.
        
        '''

        return self.chunksums.find(checksum)

    @require_open_client
    def list_chunks(self):
        '''Return list of ids of all chunks in store.'''
        result = []
        if self.fs.exists('chunks'):
            for dirname, subdirs, basenames in self.fs.depth_first('chunks'):
                for basename in basenames:
                    result.append(int(basename, 16))
        return result

    @require_started_generation
    def put_chunk_group(self, chunkids, checksum):
        '''Put a new chunk group in the store.
        
        Return identifier of new group.
        
        '''

        while True:
            cgid = random.randint(0, 2**64 - 1)
            if not self.chunkgroups.group_exists(cgid):
                break
        self.chunkgroups.add(cgid, chunkids)
        self.groupsums.add(checksum, cgid)
        return cgid

    @require_open_client
    def get_chunk_group(self, cgid):
        '''Return list of chunk ids in the given chunk group.'''
        return self.chunkgroups.list_chunk_group_chunks(cgid)

    @require_open_client
    def find_chunk_groups(self, checksum):
        '''Return list of ids of chunk groups with given checksum.'''
        return self.groupsums.find(checksum)

    @require_open_client
    def list_chunk_groups(self):
        '''Return list of ids of all chunk groups in store.'''
        return self.chunkgroups.list_chunk_groups()

    @require_open_client
    def get_file_chunks(self, gen, filename):
        '''Return list of ids of chunks belonging to a file.'''
        return self.genstore.get_file_chunks(gen, filename)

    @require_started_generation
    def set_file_chunks(self, filename, chunkids):
        '''Set ids of chunks belonging to a file.
        
        File must be in the started generation.
        
        '''
        
        self.genstore.set_file_chunks(filename, chunkids)

    @require_open_client
    def get_file_chunk_groups(self, gen, filename):
        '''Return list of ids of chunk groups belonging to a file.'''
        return self.genstore.get_file_chunk_groups(gen, filename)

    @require_started_generation
    def set_file_chunk_groups(self, filename, cgids):
        '''Set ids of chunk groups belonging to a file.
        
        File must be in the started generation.
        
        '''

        self.genstore.set_file_chunk_groups(filename, cgids)

    @require_open_client
    def genspec(self, spec):
        '''Interpret a generation specification.'''

        gens = self.list_generations()
        if not gens:
            raise obnamlib.Error('No generations')
        if spec == 'latest':
            return gens[-1]
        else:
            try:
                intspec = int(spec)
            except ValueError:
                raise obnamlib.Error('Generation %s is not an integer' % spec)
            if intspec in gens:
                return intspec
            else:
                raise obnamlib.Error('Generation %s not found' % spec)
