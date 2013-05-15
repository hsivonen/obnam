# Copyright (C) 2009-2013  Lars Wirzenius
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


import errno
import hashlib
import larch
import logging
import os
import random
import re
import stat
import struct
import time
import tracing

import obnamlib


class LockFail(obnamlib.Error):

    pass


class BadFormat(obnamlib.Error):

    pass


class HookedFS(object):

    '''A class to filter read/written data through hooks.'''

    def __init__(self, repo, fs, hooks):
        self.repo = repo
        self.fs = fs
        self.hooks = hooks

    def __getattr__(self, name):
        return getattr(self.fs, name)

    def _get_toplevel(self, filename):
        parts = filename.split(os.sep)
        if len(parts) > 1:
            return parts[0]
        else: # pragma: no cover
            raise obnamlib.Error('File at repository root: %s' % filename)

    def cat(self, filename, runfilters=True):
        data = self.fs.cat(filename)
        toplevel = self._get_toplevel(filename)
        if not runfilters:
            return data
        return self.hooks.filter_read('repository-data', data,
                                      repo=self.repo, toplevel=toplevel)

    def lock(self, filename, data):
        self.fs.lock(filename, data)

    def write_file(self, filename, data, runfilters=True):
        tracing.trace('writing hooked %s' % filename)
        toplevel = self._get_toplevel(filename)
        if runfilters:
            data = self.hooks.filter_write('repository-data', data,
                                           repo=self.repo, toplevel=toplevel)
        self.fs.write_file(filename, data)

    def overwrite_file(self, filename, data, runfilters=True):
        tracing.trace('overwriting hooked %s' % filename)
        toplevel = self._get_toplevel(filename)
        if runfilters:
            data = self.hooks.filter_write('repository-data', data,
                                           repo=self.repo, toplevel=toplevel)
        self.fs.overwrite_file(filename, data)


class Repository(object):

    '''Repository for backup data.

    Backup data is put on a virtual file system
    (obnamlib.VirtualFileSystem instance), in some form that
    the API of this class does not care about.

    The repository may contain data for several clients that share
    encryption keys. Each client is identified by a name.

    The repository has a "root" object, which is conceptually a list of
    client names.

    Each client in turn is conceptually a list of generations,
    which correspond to snapshots of the user data that existed
    when the generation was created.

    Read-only access to the repository does not require locking.
    Write access may affect only the root object, or only a client's
    own data, and thus locking may affect only the root, or only
    the client.

    When a new generation is started, it is a copy-on-write clone
    of the previous generation, and the caller needs to modify
    the new generation to match the current state of user data.

    The file 'metadata/format' at the root of the repository contains the
    version of the repository format it uses. The version is
    specified using a single integer.

    '''

    format_version = 6

    def __init__(self, fs, node_size, upload_queue_size, lru_size, hooks,
                 idpath_depth, idpath_bits, idpath_skip, current_time,
                 lock_timeout, client_name):

        self.current_time = current_time
        self.setup_hooks(hooks or obnamlib.HookManager())
        self.fs = HookedFS(self, fs, self.hooks)
        self.node_size = node_size
        self.upload_queue_size = upload_queue_size
        self.lru_size = lru_size

        hider = hashlib.md5()
        hider.update(client_name)

        self.lockmgr = obnamlib.LockManager(self.fs, lock_timeout,
                                            hider.hexdigest())

        self.got_root_lock = False
        self._open_client_list()
        self.got_shared_lock = False
        self.got_client_lock = False
        self.current_client = None
        self.current_client_id = None
        self.new_generation = None
        self.added_clients = []
        self.removed_clients = []
        self.removed_generations = []
        self.client = None
        self._open_shared()
        self.prev_chunkid = None
        self.chunk_idpath = larch.IdPath('chunks', idpath_depth,
                                         idpath_bits, idpath_skip)
        self._chunks_exists = False

    def _open_client_list(self):
        self.clientlist = obnamlib.ClientList(self.fs, self.node_size,
                                              self.upload_queue_size,
                                              self.lru_size, self)

    def _open_shared(self):
        self.chunklist = obnamlib.ChunkList(self.fs, self.node_size,
                                            self.upload_queue_size,
                                            self.lru_size, self)
        self.chunksums = obnamlib.ChecksumTree(self.fs, 'chunksums',
                                               len(self.checksum('')),
                                               self.node_size,
                                               self.upload_queue_size,
                                               self.lru_size, self)

    def setup_hooks(self, hooks):
        self.hooks = hooks

        self.hooks.new('repository-toplevel-init')
        self.hooks.new_filter('repository-data')
        self.hooks.new('repository-add-client')

    def checksum(self, data):
        '''Return checksum of data.

        The checksum is (currently) MD5.

        '''

        checksummer = self.new_checksummer()
        checksummer.update(data)
        return checksummer.hexdigest()

    def new_checksummer(self):
        '''Return a new checksum algorithm.'''
        return hashlib.md5()

    def acceptable_version(self, version):
        '''Are we compatible with on-disk format?'''
        return self.format_version == version

    def list_clients(self):
        '''Return list of names of clients using this repository.'''

        self.check_format_version()
        listed = set(self.clientlist.list_clients())
        added = set(self.added_clients)
        removed = set(self.removed_clients)
        clients = listed.union(added).difference(removed)
        return list(clients)

    def require_root_lock(self):
        '''Ensure we have the lock on the repository's root node.'''
        if not self.got_root_lock:
            raise LockFail('have not got lock on root node')

    def require_shared_lock(self):
        '''Ensure we have the lock on the shared B-trees except clientlist.'''
        if not self.got_shared_lock:
            raise LockFail('have not got lock on shared B-trees')

    def require_client_lock(self):
        '''Ensure we have the lock on the currently open client.'''
        if not self.got_client_lock:
            raise LockFail('have not got lock on client')

    def require_open_client(self):
        '''Ensure we have opened the client (r/w or r/o).'''
        if self.current_client is None:
            raise obnamlib.Error('client is not open')

    def require_started_generation(self):
        '''Ensure we have started a new generation.'''
        if self.new_generation is None:
            raise obnamlib.Error('new generation has not started')

    def require_no_root_lock(self):
        '''Ensure we haven't locked root yet.'''
        if self.got_root_lock:
            raise obnamlib.Error('We have already locked root, oops')

    def require_no_shared_lock(self):
        '''Ensure we haven't locked shared B-trees yet.'''
        if self.got_shared_lock:
            raise obnamlib.Error('We have already locked shared B-trees, oops')

    def require_no_client_lock(self):
        '''Ensure we haven't locked the per-client B-tree yet.'''
        if self.got_client_lock:
            raise obnamlib.Error('We have already locked the client, oops')

    def lock_root(self):
        '''Lock root node.

        Raise obnamlib.LockFail if locking fails. Lock will be released
        by commit_root() or unlock_root().

        '''

        tracing.trace('locking root')
        self.require_no_root_lock()
        self.require_no_client_lock()
        self.require_no_shared_lock()

        self.lockmgr.lock(['.'])
        self.check_format_version()
        self.got_root_lock = True
        self.added_clients = []
        self.removed_clients = []
        self._write_format_version(self.format_version)
        self.clientlist.start_changes()

    def unlock_root(self):
        '''Unlock root node without committing changes made.'''
        tracing.trace('unlocking root')
        self.require_root_lock()
        self.added_clients = []
        self.removed_clients = []
        self.lockmgr.unlock(['.'])
        self.got_root_lock = False
        self._open_client_list()

    def commit_root(self):
        '''Commit changes to root node, and unlock it.'''
        tracing.trace('committing root')
        self.require_root_lock()
        for client_name in self.added_clients:
            self.clientlist.add_client(client_name)
            self.hooks.call('repository-add-client',
                            self.clientlist, client_name)
        self.added_clients = []
        for client_name in self.removed_clients:
            client_id = self.clientlist.get_client_id(client_name)
            client_dir = self.client_dir(client_id)
            if client_id is not None and self.fs.exists(client_dir):
                self.fs.rmtree(client_dir)
            self.clientlist.remove_client(client_name)
        self.clientlist.commit()
        self.unlock_root()

    def get_format_version(self):
        '''Return (major, minor) of the on-disk format version.

        If on-disk repository does not have a version yet, return None.

        '''

        if self.fs.exists('metadata/format'):
            data = self.fs.cat('metadata/format', runfilters=False)
            lines = data.splitlines()
            line = lines[0]
            try:
                version = int(line)
            except ValueError, e: # pragma: no cover
                msg = ('Invalid repository format version (%s) -- '
                            'forgot encryption?' %
                       repr(line))
                raise obnamlib.Error(msg)
            return version
        else:
            return None

    def _write_format_version(self, version):
        '''Write the desired format version to the repository.'''
        tracing.trace('write format version')
        if not self.fs.exists('metadata'):
            self.fs.mkdir('metadata')
        self.fs.overwrite_file('metadata/format', '%s\n' % version,
                               runfilters=False)

    def check_format_version(self):
        '''Verify that on-disk format version is compatbile.

        If not, raise BadFormat.

        '''

        on_disk = self.get_format_version()
        if on_disk is not None and not self.acceptable_version(on_disk):
            raise BadFormat('On-disk repository format %s is incompatible '
                            'with program format %s; you need to use a '
                            'different version of Obnam' %
                                (on_disk, self.format_version))

    def add_client(self, client_name):
        '''Add a new client to the repository.'''
        tracing.trace('client_name=%s', client_name)
        self.require_root_lock()
        if client_name in self.list_clients():
            raise obnamlib.Error('client %s already exists in repository' %
                                 client_name)
        self.added_clients.append(client_name)

    def remove_client(self, client_name):
        '''Remove a client from the repository.

        This removes all data related to the client, including all
        actual file data unless other clients also use it.

        '''

        tracing.trace('client_name=%s', client_name)
        self.require_root_lock()
        if client_name not in self.list_clients():
            raise obnamlib.Error('client %s does not exist' % client_name)
        self.removed_clients.append(client_name)

    @property
    def shared_dirs(self):
        return [self.chunklist.dirname, self.chunksums.dirname,
                self.chunk_idpath.dirname]

    def lock_shared(self):
        '''Lock a client for exclusive write access.

        Raise obnamlib.LockFail if locking fails. Lock will be released
        by commit_client() or unlock_client().

        '''

        tracing.trace('locking shared')
        self.require_no_shared_lock()
        self.check_format_version()
        self.lockmgr.lock(self.shared_dirs)
        self.got_shared_lock = True
        tracing.trace('starting changes in chunksums and chunklist')
        self.chunksums.start_changes()
        self.chunklist.start_changes()

        # Initialize the chunks directory for encryption, etc, if it just
        # got created.
        dirname = self.chunk_idpath.dirname
        filenames = self.fs.listdir(dirname)
        if filenames == [] or filenames == ['lock']:
            self.hooks.call('repository-toplevel-init', self, dirname)


    def commit_shared(self):
        '''Commit changes to shared B-trees.'''

        tracing.trace('committing shared')
        self.require_shared_lock()
        self.chunklist.commit()
        self.chunksums.commit()
        self.unlock_shared()

    def unlock_shared(self):
        '''Unlock currently locked shared B-trees.'''
        tracing.trace('unlocking shared')
        self.require_shared_lock()
        self.lockmgr.unlock(self.shared_dirs)
        self.got_shared_lock = False
        self._open_shared()

    def lock_client(self, client_name):
        '''Lock a client for exclusive write access.

        Raise obnamlib.LockFail if locking fails. Lock will be released
        by commit_client() or unlock_client().

        '''

        tracing.trace('client_name=%s', client_name)
        self.require_no_client_lock()
        self.require_no_shared_lock()

        self.check_format_version()
        client_id = self.clientlist.get_client_id(client_name)
        if client_id is None:
            raise LockFail('client %s does not exist' % client_name)

        client_dir = self.client_dir(client_id)
        if not self.fs.exists(client_dir):
            self.fs.mkdir(client_dir)
            self.hooks.call('repository-toplevel-init', self, client_dir)

        self.lockmgr.lock([client_dir])
        self.got_client_lock = True
        self.current_client = client_name
        self.current_client_id = client_id
        self.added_generations = []
        self.removed_generations = []
        self.client = obnamlib.ClientMetadataTree(self.fs, client_dir,
                                                  self.node_size,
                                                  self.upload_queue_size,
                                                  self.lru_size, self)
        self.client.init_forest()

    def unlock_client(self):
        '''Unlock currently locked client, without committing changes.'''
        tracing.trace('unlocking client')
        self.require_client_lock()
        self.new_generation = None
        self._really_remove_generations(self.added_generations)
        self.lockmgr.unlock([self.client.dirname])
        self.client = None # FIXME: This should remove uncommitted data.
        self.added_generations = []
        self.removed_generations = []
        self.got_client_lock = False
        self.current_client = None
        self.current_client_id = None

    def commit_client(self, checkpoint=False):
        '''Commit changes to and unlock currently locked client.'''
        tracing.trace('committing client (checkpoint=%s)', checkpoint)
        self.require_client_lock()
        self.require_shared_lock()
        commit_client = self.new_generation or self.removed_generations
        if self.new_generation:
            self.client.set_current_generation_is_checkpoint(checkpoint)
        self.added_generations = []
        self._really_remove_generations(self.removed_generations)
        if commit_client:
            self.client.commit()
        self.unlock_client()

    def open_client(self, client_name):
        '''Open a client for read-only operation.'''
        tracing.trace('open r/o client_name=%s' % client_name)
        self.check_format_version()
        client_id = self.clientlist.get_client_id(client_name)
        if client_id is None:
            raise obnamlib.Error('%s is not an existing client' % client_name)
        self.current_client = client_name
        self.current_client_id = client_id
        client_dir = self.client_dir(client_id)
        self.client = obnamlib.ClientMetadataTree(self.fs, client_dir,
                                                  self.node_size,
                                                  self.upload_queue_size,
                                                  self.lru_size, self)
        self.client.init_forest()

    def list_generations(self):
        '''List existing generations for currently open client.'''
        self.require_open_client()
        return self.client.list_generations()

    def get_is_checkpoint(self, genid):
        '''Is a generation a checkpoint one?'''
        self.require_open_client()
        return self.client.get_is_checkpoint(genid)

    def start_generation(self):
        '''Start a new generation.

        The new generation is a copy-on-write clone of the previous
        one (or empty, if first generation).

        '''
        tracing.trace('start new generation')
        self.require_client_lock()
        if self.new_generation is not None:
            raise obnamlib.Error('Cannot start two new generations')
        self.client.start_generation()
        self.new_generation = \
            self.client.get_generation_id(self.client.tree)
        self.added_generations.append(self.new_generation)
        return self.new_generation

    def _really_remove_generations(self, remove_genids):
        '''Really remove a list of generations.

        This is not part of the public API.

        This does not make any safety checks.

        '''

        def find_chunkids_in_gens(genids):
            chunkids = set()
            for genid in genids:
                x = self.client.list_chunks_in_generation(genid)
                chunkids = chunkids.union(set(x))
            return chunkids

        def find_gens_to_keep():
            return [genid
                    for genid in self.list_generations()
                    if genid not in remove_genids]

        def remove_chunks(chunk_ids):
            for chunk_id in chunk_ids:
                try:
                    checksum = self.chunklist.get_checksum(chunk_id)
                except KeyError:
                    # No checksum, therefore it can't be shared, therefore
                    # we can remove it.
                    self.remove_chunk(chunk_id)
                else:
                    self.chunksums.remove(checksum, chunk_id,
                                          self.current_client_id)
                    if not self.chunksums.chunk_is_used(checksum, chunk_id):
                        self.remove_chunk(chunk_id)

        def remove_gens(genids):
            if self.new_generation is None:
                self.client.start_changes(create_tree=False)
            for genid in genids:
                self.client.remove_generation(genid)

        if not remove_genids:
            return

        self.require_client_lock()
        self.require_shared_lock()

        maybe_remove = find_chunkids_in_gens(remove_genids)
        keep_genids = find_gens_to_keep()
        keep = find_chunkids_in_gens(keep_genids)
        remove = maybe_remove.difference(keep)
        remove_chunks(remove)
        remove_gens(remove_genids)

    def remove_generation(self, gen):
        '''Remove a committed generation.'''
        self.require_client_lock()
        if gen == self.new_generation:
            raise obnamlib.Error('cannot remove started generation')
        self.removed_generations.append(gen)

    def get_generation_times(self, gen):
        '''Return start and end times of a generation.

        An unfinished generation has no end time, so None is returned.

        '''

        self.require_open_client()
        return self.client.get_generation_times(gen)

    def listdir(self, gen, dirname):
        '''Return list of basenames in a directory within generation.'''
        self.require_open_client()
        return self.client.listdir(gen, dirname)

    def get_metadata(self, gen, filename):
        '''Return metadata for a file in a generation.'''

        self.require_open_client()
        try:
            encoded = self.client.get_metadata(gen, filename)
        except KeyError:
            raise obnamlib.Error('%s does not exist' % filename)
        return obnamlib.decode_metadata(encoded)

    def create(self, filename, metadata):
        '''Create a new (empty) file in the new generation.'''
        self.require_started_generation()
        encoded = obnamlib.encode_metadata(metadata)
        self.client.create(filename, encoded)

    def remove(self, filename):
        '''Remove file or directory or directory tree from generation.'''
        self.require_started_generation()
        self.client.remove(filename)

    def _chunk_filename(self, chunkid):
        return self.chunk_idpath.convert(chunkid)

    def put_chunk_only(self, data):
        '''Put chunk of data into repository.

        If the same data is already in the repository, it will be put there
        a second time. It is the caller's responsibility to check
        that the data is not already in the repository.

        Return the unique identifier of the new chunk.

        '''

        def random_chunkid():
            return random.randint(0, obnamlib.MAX_ID)

        self.require_started_generation()

        if self.prev_chunkid is None:
            self.prev_chunkid = random_chunkid()

        while True:
            chunkid = (self.prev_chunkid + 1) % obnamlib.MAX_ID
            filename = self._chunk_filename(chunkid)
            try:
                self.fs.write_file(filename, data)
            except OSError, e: # pragma: no cover
                if e.errno == errno.EEXIST:
                    self.prev_chunkid = random_chunkid()
                    continue
                raise
            else:
                tracing.trace('chunkid=%s', chunkid)
                break

        self.prev_chunkid = chunkid
        return chunkid

    def put_chunk_in_shared_trees(self, chunkid, checksum):
        '''Put the chunk into the shared trees.

        The chunk is assumed to already exist in the repository, so we
        just need to add it to the shared trees that map chunkids to
        checksums and checksums to chunkids.

        '''

        tracing.trace('chunkid=%s', chunkid)
        tracing.trace('checksum=%s', repr(checksum))

        self.require_started_generation()
        self.require_shared_lock()

        self.chunklist.add(chunkid, checksum)
        self.chunksums.add(checksum, chunkid, self.current_client_id)

    def get_chunk(self, chunkid):
        '''Return data of chunk with given id.'''
        self.require_open_client()
        return self.fs.cat(self._chunk_filename(chunkid))

    def chunk_exists(self, chunkid):
        '''Does a chunk exist in the repository?'''
        self.require_open_client()
        return self.fs.exists(self._chunk_filename(chunkid))

    def find_chunks(self, checksum):
        '''Return identifiers of chunks with given checksum.

        Because of hash collisions, the list may be longer than one.

        '''

        self.require_open_client()
        return self.chunksums.find(checksum)

    def list_chunks(self):
        '''Return list of ids of all chunks in repository.'''
        result = []
        pat = re.compile(r'^.*/.*/[0-9a-fA-F]+$')
        if self.fs.exists('chunks'):
            for pathname, st in self.fs.scan_tree('chunks'):
                if stat.S_ISREG(st.st_mode) and pat.match(pathname):
                    basename = os.path.basename(pathname)
                    result.append(int(basename, 16))
        return result

    def remove_chunk(self, chunk_id):
        '''Remove a chunk from the repository.

        Note that this does _not_ remove the chunk from the chunk
        checksum forest. The caller is not supposed to call us until
        the chunk is not there anymore.

        However, it does remove the chunk from the chunk list forest.

        '''

        tracing.trace('chunk_id=%s', chunk_id)
        self.require_open_client()
        self.require_shared_lock()
        self.chunklist.remove(chunk_id)
        filename = self._chunk_filename(chunk_id)
        try:
            self.fs.remove(filename)
        except OSError:
            pass

    def get_file_chunks(self, gen, filename):
        '''Return list of ids of chunks belonging to a file.'''
        self.require_open_client()
        return self.client.get_file_chunks(gen, filename)

    def set_file_chunks(self, filename, chunkids):
        '''Set ids of chunks belonging to a file.

        File must be in the started generation.

        '''

        self.require_started_generation()
        self.client.set_file_chunks(filename, chunkids)

    def append_file_chunks(self, filename, chunkids):
        '''Append to list of ids of chunks belonging to a file.

        File must be in the started generation.

        '''

        self.require_started_generation()
        self.client.append_file_chunks(filename, chunkids)

    def set_file_data(self, filename, contents): # pragma: no cover
        '''Store contents of file in B-tree instead of chunks dir.'''
        self.require_started_generation()
        self.client.set_file_data(filename, contents)

    def get_file_data(self, gen, filename): # pragma: no cover
        '''Returned contents of file stored in B-tree instead of chunks dir.'''
        self.require_open_client()
        return self.client.get_file_data(gen, filename)

    def genspec(self, spec):
        '''Interpret a generation specification.'''

        self.require_open_client()
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

    def walk(self, gen, arg, depth_first=False):
        '''Iterate over each pathname specified by argument.

        This is a generator. Each return value is a tuple consisting
        of a pathname and its corresponding metadata. Directories are
        recursed into.

        '''

        arg = os.path.normpath(arg)
        metadata = self.get_metadata(gen, arg)
        if metadata.isdir():
            if not depth_first:
                yield arg, metadata
            kids = self.listdir(gen, arg)
            kidpaths = [os.path.join(arg, kid) for kid in kids]
            for kidpath in kidpaths:
                for x in self.walk(gen, kidpath, depth_first=depth_first):
                    yield x
            if depth_first:
                yield arg, metadata
        else:
            yield arg, metadata


class RepositoryFormat6(obnamlib.RepositoryInterface):

    format = '6'

    def __init__(self,
            lock_timeout=0,
            node_size=obnamlib.DEFAULT_NODE_SIZE,
            upload_queue_size=obnamlib.DEFAULT_UPLOAD_QUEUE_SIZE,
            lru_size=obnamlib.DEFAULT_LRU_SIZE,
            hooks=None):
        self._lock_timeout = lock_timeout
        self._node_size = node_size
        self._upload_queue_size = upload_queue_size
        self._lru_size = lru_size

        self._setup_hooks(hooks or obnamlib.HookManager())

    def _setup_hooks(self, hooks):
        self.hooks = hooks
        self.hooks.new('repository-toplevel-init')
        self.hooks.new_filter('repository-data')
        self.hooks.new('repository-add-client')

    def set_fs(self, fs):
        self._fs = HookedFS(self, fs, self.hooks)
        self._lockmgr = obnamlib.LockManager(self._fs, self._lock_timeout, '')
        self._setup_client_list()
        self._setup_client()

    def init_repo(self):
        # There is nothing else to be done.
        pass

    # Client list handling.

    def _setup_client_list(self):
        self._got_client_list_lock = False
        self._client_list = obnamlib.ClientList(
            self._fs, self._node_size, self._upload_queue_size,
            self._lru_size, self)

    def _raw_lock_client_list(self):
        if self._got_client_list_lock:
            raise obnamlib.RepositoryClientListLockingFailed()
        self._lockmgr.lock(['.'])
        self._got_client_list_lock = True

    def _raw_unlock_client_list(self):
        if not self._got_client_list_lock:
            raise obnamlib.RepositoryClientListNotLocked()
        self._lockmgr.unlock(['.'])
        self._got_client_list_lock = False

    def _require_client_list_lock(self):
        if not self._got_client_list_lock:
            raise obnamlib.RepositoryClientListNotLocked()

    def lock_client_list(self):
        tracing.trace('locking client list')
        self._raw_lock_client_list()

    def unlock_client_list(self):
        tracing.trace('unlocking client list')
        self._raw_unlock_client_list()

    def commit_client_list(self):
        tracing.trace('committing client list')
        self._raw_unlock_client_list()

    def force_client_list_lock(self):
        tracing.trace('forcing client list lock')
        if self._got_client_list_lock:
            self._raw_unlock_client_list()
        self._raw_lock_client_list()

    def get_client_list(self):
        return self._client_list.list_clients()

    def add_client(self, client_name):
        self._require_client_list_lock()
        if self._client_list.get_client_id(client_name):
            raise obnamlib.RepositoryClientAlreadyExists(client_name)
        self._client_list.add_client(client_name)

    def remove_client(self, client_name):
        self._require_client_list_lock()
        if not self._client_list.get_client_id(client_name):
            raise obnamlib.RepositoryClientDoesNotExist(client_name)
        self._client_list.remove_client(client_name)

    def _get_client_id(self, client_name):
        '''Return a client's unique, filesystem-visible id.

        The id is a random 64-bit integer.

        '''

        return self._client_list.get_client_id(client_name)

    # Handling of individual clients.

    def current_time(self):
        # ClientMetadataTree wants us to provide this method.
        # FIXME: A better design would be to for us to provide
        # the class with a function to call.
        return time.time()

    def _setup_client(self):
        # We keep a list of all open clients. An open client may or
        # may not be locked. Each value in the dict is a tuple of
        # ClientMetadataTree and is_locked.
        self._open_clients = {}

    def _get_client_dir(self, client_id):
        '''Return name of sub-directory for a given client.'''
        return str(client_id)

    def _client_is_locked(self, client_name):
        return self._open_clients.get(client_name, (None, False))[1]

    def _require_client_lock(self, client_name):
        if client_name not in self.get_client_list():
            raise obnamlib.RepositoryClientDoesNotExist(client_name)
        if not self._client_is_locked(client_name):
            raise obnamlib.RepositoryClientNotLocked(client_name)

    def _raw_lock_client(self, client_name):
        tracing.trace('client_name=%s', client_name)

        if self._client_is_locked(client_name):
            raise obnamlib.RepositoryClientLockingFailed(client_name)

        client_id = self._get_client_id(client_name)
        if client_id is None:
            raise obnamlib.RepositoryClientDoesNotExist(client_name)

        # Create and initialise the client's own directory, if needed.
        client_dir = self._get_client_dir(client_id)
        if not self._fs.exists(client_dir):
            self._fs.mkdir(client_dir)
            self.hooks.call('repository-toplevel-init', self, client_dir)

        # Actually lock the directory.
        self._lockmgr.lock([client_dir])

        # Create the per-client B-tree instance.
        client = obnamlib.ClientMetadataTree(
            self._fs, client_dir, self._node_size, self._upload_queue_size,
            self._lru_size, self)
        client.init_forest()

        # Remember, remember, the 5th of November.
        self._open_clients[client_name] = (client, True)

    def _raw_unlock_client(self, client_name):
        tracing.trace('client_name=%s', client_name)
        self._require_client_lock(client_name)

        client, is_locked = self._open_clients[client_name]
        self._lockmgr.unlock([client.dirname])
        del self._open_clients[client_name]

    def lock_client(self, client_name):
        logging.info('Locking client %s' % client_name)
        self._raw_lock_client(client_name)

    def unlock_client(self, client_name):
        logging.info('Unlocking client %s' % client_name)
        self._raw_unlock_client(client_name)

    def get_allowed_client_keys(self):
        return [obnamlib.REPO_CLIENT_TEST_KEY]
