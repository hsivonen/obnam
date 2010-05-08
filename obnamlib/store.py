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


# NOTE: THIS IS EXTREMELY NOT INTENDED TO BE PRODUCTION READY. THIS
# WHOLE MODULE EXISTS ONLY TO PLAY WITH THE INTERFACE. THE IMPLEMENTATION
# IS TOTALLY STUPID.


import btree
import errno
import hashlib
import os
import pickle
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


def require_host_lock(method):
    '''Decorator for ensuring the currently open host is locked by us.'''
    
    def helper(self, *args, **kwargs):
        if not self.got_host_lock:
            raise LockFail('have not got lock on host')
        return method(self, *args, **kwargs)
    
    return helper


def require_open_host(method):
    '''Decorator for ensuring store has an open host.
    
    Host may be read/write (locked) or read-only.
    
    '''
    
    def helper(self, *args, **kwargs):
        if self.current_host is None:
            raise obnamlib.Error('host is not open')
        return method(self, *args, **kwargs)
    
    return helper


def require_started_generation(method):
    '''Decorator for ensuring a new generation has been started. '''
    
    def helper(self, *args, **kwargs):
        if self.new_generation is None:
            raise obnamlib.Error('new generation has not started')
        return method(self, *args, **kwargs)
    
    return helper


def encode_metadata(metadata):
    return pickle.dumps(metadata)
    

def decode_metadata(encoded):
    return pickle.loads(encoded)


class NodeStoreVfs(btree.NodeStoreDisk):

    def __init__(self, fs, dirname, node_size, codec):
        btree.NodeStoreDisk.__init__(self, dirname, node_size, codec)
        self.fs = fs

    def read_file(self, filename):
        return self.fs.cat(filename)

    def write_file(self, filename, contents):
        self.fs.overwrite_file(filename, contents)

    def file_exists(self, filename):
        return self.fs.exists(filename)

    def rename_file(self, old, new):
        self.fs.rename(old, new)

    def remove_file(self, filename):
        self.fs.remove(filename)

    def listdir(self, dirname): # pragma: no cover
        return self.fs.listdir(dirname)


class HostList(object):

    '''Store list of hosts.'''

    key_bytes = 8 # 64-bit counter as key
    node_size = 4096 # typical size of disk block

    def __init__(self, fs):
        self.fs = fs
        self.forest = None
        self.minkey = self.key(0)
        self.maxkey = self.key(2**64-1)

    def key(self, intkey):
        return struct.pack('!Q', intkey)

    def init_forest(self, create=False):
        if self.forest is None:
            if create:
                if not self.fs.exists('hostlist'):
                    self.fs.mkdir('hostlist')
            elif not self.fs.exists('hostlist'):
                return False
            codec = btree.NodeCodec(self.key_bytes)
            ns = NodeStoreVfs(self.fs, 'hostlist', self.node_size, codec)
            self.forest = btree.Forest(ns)
        return True

    def require_forest(self): # pragma: no cover
        if not self.init_forest(create=True):
            raise obnamlib.Error('Cannot initialize %s as host list' %
                                 (os.path.join(self.fs.getcwd(), 'hostlist')))

    def pairs(self): # pragma: no cover
        if self.forest.trees:
            t = self.forest.trees[-1]
            return t.lookup_range(self.minkey, self.maxkey)
        else:
            return []

    def list_hosts(self):
        if not self.init_forest():
            return []
        return [value for key, value in self.pairs()]

    def add_host(self, hostname):
        self.require_forest()
        if not self.forest.trees:
            t = self.forest.new_tree()
            hostnum = 0
        else:
            t = self.forest.new_tree(old=self.forest.trees[-1])
            pairs = t.lookup_range(self.minkey, self.maxkey)
            biggest = max(key for key, value in pairs)
            hostnum = 1 + struct.unpack('!Q', biggest)[0]
        t.insert(self.key(hostnum), hostname)

    def remove_host(self, hostname):
        self.require_forest()
        if self.forest.trees:
            t = self.forest.new_tree(old=self.forest.trees[-1])
            for key, value in t.lookup_range(self.minkey, self.maxkey):
                if value == hostname:
                    t.remove(key)
                    break

    def commit(self):
        self.require_forest()
        self.forest.commit()


class GenerationStore(object):

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
      * subkey is ordinal

    '''

    node_size = 64 * 1024

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

    FILE_NAME = 0
    FILE_METADATA = 1
    
    def __init__(self, fs, hostname):
        self.fs = fs
        self.dirname = hostname # FIXME: This needs to handle evil hostnames
        self.forest = None
        self.curgen = None
        self.key_bytes = len(self.key('', 0, 0))

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

    def unkey(self, key):
        '''Split a key into its components.'''
        return struct.unpack('!8sB8s', key)

    def unkey_int(self, key):
        '''Split a key into its components, with subkey being an integer.'''
        return struct.unpack('!8sBQ', key)

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

    def init_forest(self, create=False):
        if self.forest is None:
            exists = self.fs.exists(self.dirname)
            if not exists:
                if create:
                    self.fs.mkdir(self.dirname)
                else:
                    return False
            codec = btree.NodeCodec(self.key_bytes)
            ns = NodeStoreVfs(self.fs, self.dirname, self.node_size, codec)
            self.forest = btree.Forest(ns)
        return True

    def require_forest(self): # pragma: no cover
        if not self.init_forest(create=True):
            name = os.path.join(self.fs.getcwd(), self.dirname)
            raise obnamlib.Error('Cannot initialize %s as host list' % name)

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
        key = self.genkey(self.GEN_META_ID)
        for t in self.forest.trees:
            if self._lookup_int(t, key) == genid:
                return t
        raise KeyError('Unknown generation %s' % genid)

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
        try:
            self.curgen.remove_range(minkey, maxkey)
        except KeyError:
            pass

        # Also remove from parent's contents.
        parent = os.path.dirname(filename)
        if parent != filename: # root dir is its own parent
            h = self.hash_name(filename)
            minkey = self.key(parent, self.DIR_CONTENTS, 0)
            maxkey = self.key(parent, self.DIR_CONTENTS, self.SUBKEY_MAX)
            pairs = self.curgen.lookup_range(minkey, maxkey)
            for key, value in pairs:
                if value == h:
                    self.curgen.remove(key)
                    break

    def create(self, filename, metadata):
        self._remove_filename_data(filename)
        self.set_metadata(filename, metadata)

        # Add to parent's contents.
        parent = os.path.dirname(filename)
        if parent != filename: # root dir is its own parent
            h = self.hash_name(filename)
            minkey = self.key(parent, self.DIR_CONTENTS, 0)
            maxkey = self.key(parent, self.DIR_CONTENTS, self.SUBKEY_MAX)
            pairs = self.curgen.lookup_range(minkey, maxkey)
            if pairs:
                a, b, maxindex = self.unkey_int(pairs[-1][0])
                index = maxindex + 1
            else:
                index = 0
            self.curgen.insert(self.key(parent, self.DIR_CONTENTS, index), h)

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
            namekey = self.hashkey(value, self.FILE, self.FILE_NAME)
            pathname = tree.lookup(namekey)
            basenames.append(os.path.basename(pathname))
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


class Store(object):

    '''Store backup data.
    
    Backup data is stored on a virtual file system
    (obnamlib.VirtualFileSystem instance), in some form that
    the API of this class does not care about.
    
    The store may contain data for several hosts that share 
    encryption keys. Each host is identified by a name.
    
    The store has a "root" object, which is conceptually a list of
    host names.
    
    Each host in turn is conceptually a list of generations,
    which correspond to snapshots of the user data that existed
    when the generation was created.
    
    Read-only access to the store does not require locking.
    Write access may affect only the root object, or only a host's
    own data, and thus locking may affect only the root, or only
    the host.
    
    When a new generation is started, it is a copy-on-write clone
    of the previous generation, and the caller needs to modify
    the new generation to match the current state of user data.

    '''

    def __init__(self, fs):
        self.fs = fs
        self.got_root_lock = False
        self.hostlist = HostList(fs)
        self.got_host_lock = False
        self.host_lockfile = None
        self.current_host = None
        self.new_generation = None
        self.added_hosts = []
        self.removed_hosts = []
        self.removed_generations = []
        self.genstore = None

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

    def list_hosts(self):
        '''Return list of names of hosts using this store.'''

        listed = set(self.hostlist.list_hosts())
        added = set(self.added_hosts)
        removed = set(self.removed_hosts)
        hosts = listed.union(added).difference(removed)
        return list(hosts)

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
        self.added_hosts = []
        self.removed_hosts = []

    @require_root_lock
    def unlock_root(self):
        '''Unlock root node without committing changes made.'''
        for hostname in self.added_hosts:
            if self.fs.exists(hostname):
                self.fs.rmtree(hostname) # FIXME
        self.added_hosts = []
        self.removed_hosts = []
        self.fs.remove('root.lock')
        self.got_root_lock = False
        
    @require_root_lock
    def commit_root(self):
        '''Commit changes to root node, and unlock it.'''
        for hostname in self.added_hosts:
            self.hostlist.add_host(hostname)
        self.added_hosts = []
        for hostname in self.removed_hosts:
            if self.fs.exists(hostname):
                self.fs.rmtree(hostname) # FIXME
            self.hostlist.remove_host(hostname)
        self.hostlist.commit()
        self.unlock_root()
        
    @require_root_lock
    def add_host(self, hostname):
        '''Add a new host to the store.'''
        if hostname in self.list_hosts():
            raise obnamlib.Error('host %s already exists in store' % hostname)
        self.added_hosts.append(hostname)
        
    @require_root_lock
    def remove_host(self, hostname):
        '''Remove a host from the store.
        
        This removes all data related to the host, including all
        actual file data unless other hosts also use it.
        
        '''
        
        if hostname not in self.list_hosts():
            raise obnamlib.Error('host %s does not exist' % hostname)
        self.removed_hosts.append(hostname)
        
    def lock_host(self, hostname):
        '''Lock a host for exclusive write access.
        
        Raise obnamlib.LockFail if locking fails. Lock will be released
        by commit_host() or unlock_host().

        '''
        
        lockname = os.path.join(hostname, 'lock')
        try:
            self.fs.write_file(lockname, '')
        except OSError, e:
            if e.errno == errno.EEXIST:
                raise LockFail('Host %s is already locked' % hostname)
        self.got_host_lock = True
        self.host_lockfile = lockname
        self.current_host = hostname
        self.added_generations = []
        self.removed_generations = []
        self.genstore = GenerationStore(self.fs, hostname)
        self.genstore.require_forest()

    @require_host_lock
    def unlock_host(self):
        '''Unlock currently locked host, without committing changes.'''
        self.new_generation = None
        for genid in self.added_generations:
            self._really_remove_generation(genid)
        self.genstore = None # FIXME: This should remove uncommitted data.
        self.added_generations = []
        self.removed_generations = []
        self.fs.remove(self.host_lockfile)
        self.host_lockfile = None
        self.got_host_lock = False
        self.current_host = None

    @require_host_lock
    def commit_host(self):
        '''Commit changes to and unlock currently locked host.'''
        self.added_generations = []
        for genid in self.removed_generations:
            self._really_remove_generation(genid)
        self.genstore.commit()
        self.unlock_host()
        
    def open_host(self, hostname):
        '''Open a host for read-only operation.'''
        if hostname not in self.list_hosts():
            raise obnamlib.Error('%s is not an existing host' % hostname)
        self.current_host = hostname
        self.genstore = GenerationStore(self.fs, hostname)
        self.genstore.init_forest()
        
    @require_open_host
    def list_generations(self):
        '''List existing generations for currently open host.'''
        return self.genstore.list_generations()
        
    @require_host_lock
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

    @require_host_lock
    def _really_remove_generation(self, gen):
        '''Really remove a committed generation.
        
        This is not part of the public API.
        
        This does not make any safety checks.
        
        '''

        self.genstore.remove_generation(gen)

    @require_host_lock
    def remove_generation(self, gen):
        '''Remove a committed generation.'''
        if gen == self.new_generation:
            raise obnamlib.Error('cannot remove started generation')
        self.removed_generations.append(gen)

    @require_open_host
    def get_generation_times(self, gen):
        '''Return start and end times of a generation.
        
        An unfinished generation has no end time, so None is returned.
        
        '''

        return self.genstore.get_generation_times(gen)

    @require_open_host
    def listdir(self, gen, dirname):
        '''Return list of basenames in a directory within generation.'''
        return self.genstore.listdir(gen, dirname)
        
    @require_open_host
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
        return os.path.join('chunks', chunkid)

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
        
        i = 0
        while True:
            i += 1
            chunkid = '%d' % i
            filename = self._chunk_filename(chunkid)
            if not self.fs.exists(filename):
                break
        self.fs.write_file(filename, data)
        return chunkid
        
    @require_open_host
    def get_chunk(self, chunkid):
        '''Return data of chunk with given id.'''
        
        return self.fs.cat(self._chunk_filename(chunkid))
        
    @require_open_host
    def chunk_exists(self, chunkid):
        '''Does a chunk exist in the store?'''
        return self.fs.exists(self._chunk_filename(chunkid))
        
    @require_open_host
    def find_chunks(self, checksum):
        '''Return identifiers of chunks with given checksum.
        
        Because of hash collisions, the list may be longer than one.
        
        '''

        chunkids = []
        if self.fs.exists('chunks'):
            for chunkid in self.fs.listdir('chunks'):
                filename = self._chunk_filename(chunkid)
                data = self.fs.cat(filename)
                if self.checksum(data) == checksum:
                    chunkids.append(chunkid)
        return chunkids

    @require_open_host
    def list_chunks(self):
        '''Return list of ids of all chunks in store.'''
        if self.fs.exists('chunks'):
            return self.fs.listdir('chunks')
        else:
            return []

    def _chunk_group_filename(self, cgid):
        return os.path.join('chunkgroups', cgid)

    @require_started_generation
    def put_chunk_group(self, chunkids, checksum):
        '''Put a new chunk group in the store.
        
        Return identifier of new group.
        
        '''

        i = 0
        while True:
            i += 1
            cgid = '%d' % i
            filename = self._chunk_group_filename(cgid)
            if not self.fs.exists(filename):
                break
        data = ''.join('%s\n' % x for x in [checksum] + chunkids)
        self.fs.write_file(filename, data)
        return cgid

    @require_open_host
    def get_chunk_group(self, cgid):
        '''Return list of chunk ids in the given chunk group.'''

        filename = self._chunk_group_filename(cgid)
        data = self.fs.cat(filename)
        lines = data.splitlines()
        return lines[1:]
        
    @require_open_host
    def find_chunk_groups(self, checksum):
        '''Return list of ids of chunk groups with given checksum.'''
        
        cgids = []
        if self.fs.exists('chunkgroups'):
            for cgid in self.fs.listdir('chunkgroups'):
                filename = self._chunk_group_filename(cgid)
                data = self.fs.cat(filename)
                lines = data.splitlines()
                if lines[0] == checksum:
                    cgids.append(cgid)
        return cgids

    @require_open_host
    def list_chunk_groups(self):
        '''Return list of ids of all chunk groups in store.'''
        if self.fs.exists('chunkgroups'):
            return self.fs.listdir('chunkgroups')
        else:
            return []

    @require_open_host
    def get_file_chunks(self, gen, filename):
        '''Return list of ids of chunks belonging to a file.'''
        return self.genstore.get_file_chunks(gen, filename)

    @require_started_generation
    def set_file_chunks(self, filename, chunkids):
        '''Set ids of chunks belonging to a file.
        
        File must be in the started generation.
        
        '''
        
        self.genstore.set_file_chunks(filename, chunkids)

    @require_open_host
    def get_file_chunk_groups(self, gen, filename):
        '''Return list of ids of chunk groups belonging to a file.'''
        return self.genstore.get_file_chunk_groups(gen, filename)

    @require_started_generation
    def set_file_chunk_groups(self, filename, cgids):
        '''Set ids of chunk groups belonging to a file.
        
        File must be in the started generation.
        
        '''

        self.genstore.set_file_chunk_groups(filename, cgids)

    @require_open_host
    def genspec(self, spec):
        '''Interpret a generation specification.'''

        gens = self.list_generations()
        if not gens:
            raise obnamlib.Error('No generations')
        if spec == 'latest':
            return gens[-1]
        elif spec in gens:
            return spec
        else:
            raise obnamlib.Error('Generation %s not found' % spec)
