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


import errno
import hashlib
import os
import pickle

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
        self.got_host_lock = False
        self.host_lockfile = None
        self.current_host = None
        self.new_generation = None

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
        return [x 
                for x in self.fs.listdir('.') 
                if x not in ['chunks', 'chunk_groups'] and self.fs.isdir(x)]

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

    @require_root_lock
    def unlock_root(self):
        '''Unlock root node without committing changes made.'''
        self.fs.remove('root.lock')
        self.got_root_lock = False
        
    @require_root_lock
    def commit_root(self):
        '''Commit changes to root node, and unlock it.'''
        self.unlock_root()
        
    @require_root_lock
    def add_host(self, hostname):
        '''Add a new host to the store.'''
        if self.fs.exists(hostname):
            raise obnamlib.Error('host %s already exists in store' % hostname)
        self.fs.mkdir(hostname)
        
    @require_root_lock
    def remove_host(self, hostname):
        '''Remove a host from the store.
        
        This removes all data related to the host, including all
        actual file data unless other hosts also use it.
        
        '''
        
        if not self.fs.isdir(hostname):
            raise obnamlib.Error('host %s does not exist' % hostname)
        self.fs.rmtree(hostname)
        
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

    @require_host_lock
    def unlock_host(self):
        '''Unlock currently locked host.'''
        self.fs.remove(self.host_lockfile)
        self.host_lockfile = None
        self.got_host_lock = False
        self.current_host = None
        self.new_generation = None

    @require_host_lock
    def commit_host(self):
        '''Commit changes to and unlock currently locked host.'''
        if self.new_generation is not None:
            name = os.path.join(self.current_host, self.new_generation)
            self.fs.write_file(name + '.end', '')
        self.unlock_host()
        
    def open_host(self, hostname):
        '''Open a host for read-only operation.'''
        self.current_host = hostname
        
    @require_open_host
    def list_generations(self):
        '''List existing generations for currently open host.'''
        return sorted(x for
                      x in self.fs.listdir(self.current_host)
                      if self.fs.isdir(os.path.join(self.current_host, x)))
        
    @require_host_lock
    def start_generation(self):
        '''Start a new generation.
        
        The new generation is a copy-on-write clone of the previous
        one (or empty, if first generation).
        
        '''
        if self.new_generation is not None:
            raise obnamlib.Error('Cannot start two new generations')
        i = 0
        while True:
            i += 1
            gen = 'gen-%09d' % i
            name = os.path.join(self.current_host, gen)
            if not self.fs.exists(name):
                break
        self.new_generation = gen
        self.fs.mkdir(name)
        self.fs.write_file(name + '.start', '')
        return self.new_generation

    @require_host_lock
    def remove_generation(self, gen):
        '''Remove a committed generation.'''
        if gen == self.new_generation:
            raise obnamlib.Error('cannot remove started generation')
        self.fs.rmtree(os.path.join(self.current_host, gen))

    @require_open_host
    def get_generation_times(self, gen):
        '''Return start and end times of a generation.
        
        An unfinished generation has no end time, so None is returned.
        
        '''

        start = None
        end = None
        
        name = os.path.join(self.current_host, gen)
        try:
            start = self.fs.lstat(name + '.start').st_mtime
            end = self.fs.lstat(name + '.end').st_mtime
        except OSError:
            pass

        return start, end

    def genpath(self, gen, filename):
        return os.path.join(self.current_host, gen, './' + filename)
        
    @require_open_host
    def listdir(self, gen, dirname):
        '''Return list of basenames in a directory within generation.'''
        return [x for x in self.fs.listdir(self.genpath(gen, dirname))
                if x != '.metadata']
        
    @require_open_host
    def get_metadata(self, gen, filename):
        '''Return metadata for a file in a generation.'''
        path = self.genpath(gen, filename)
        if not self.fs.exists(path):
            raise obnamlib.Error('%s does not exist' % filename)
        if self.fs.isdir(path):
            encoded = self.fs.cat(os.path.join(path, '.metadata'))
        else:
            encoded = self.fs.cat(self.genpath(gen, filename))
        return decode_metadata(encoded)

    @require_started_generation
    def _set_metadata(self, gen, filename, metadata):
        '''Internal, do not use.'''
        path = self.genpath(self.new_generation, filename)
        encoded = encode_metadata(metadata)
        if metadata.isdir():
            if not self.fs.exists(path):
                self.fs.makedirs(path)
            metaname = os.path.join(path, '.metadata')
            if self.fs.exists(metaname): # pragma: no cover
                self.fs.remove(metaname)
            self.fs.write_file(metaname, encoded)
        else:
            metaname = path
            
        if self.fs.exists(metaname):
            self.fs.remove(metaname)
        self.fs.write_file(metaname, encoded)
        
    @require_started_generation
    def create(self, filename, metadata):
        '''Create a new (empty) file in the new generation.'''

        self._set_metadata(self.new_generation, filename, metadata)

    @require_started_generation
    def remove(self, filename):
        '''Remove file or directory or directory tree from generation.'''
        x = self.genpath(self.new_generation, filename)
        if self.fs.isdir(x):
            self.fs.rmtree(x)
        else:
            self.fs.remove(x)

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
        metadata = self.get_metadata(gen, filename)
        return metadata.chunks or []

    @require_started_generation
    def set_file_chunks(self, filename, chunkids):
        '''Set ids of chunks belonging to a file.
        
        File must be in the started generation.
        
        '''
        
        metadata = self.get_metadata(self.new_generation, filename)
        if metadata.chunk_groups:
            raise obnamlib.Error('file %s already has chunk groups' % 
                                 filename)
        metadata.chunks = chunkids
        self._set_metadata(self.new_generation, filename, metadata)

    @require_open_host
    def get_file_chunk_groups(self, gen, filename):
        '''Return list of ids of chunk groups belonging to a file.'''
        metadata = self.get_metadata(gen, filename)
        return metadata.chunk_groups or []

    @require_started_generation
    def set_file_chunk_groups(self, filename, cgids):
        '''Set ids of chunk groups belonging to a file.
        
        File must be in the started generation.
        
        '''

        metadata = self.get_metadata(self.new_generation, filename)
        if metadata.chunks:
            raise obnamlib.Error('file %s already has chunks' % filename)
        metadata.chunk_groups = cgids
        self._set_metadata(self.new_generation, filename, metadata)

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
