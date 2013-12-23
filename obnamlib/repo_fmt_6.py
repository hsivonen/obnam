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
        if not runfilters: # pragma: no cover
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


class _OpenClient(object):

    def __init__(self, client):
        self.locked = False
        self.client = client
        self.current_generation_number = None
        self.removed_generation_numbers = []


class RepositoryFormat6(obnamlib.RepositoryInterface):

    format = '6'

    def __init__(self,
                 lock_timeout=0,
                 node_size=obnamlib.DEFAULT_NODE_SIZE,
                 upload_queue_size=obnamlib.DEFAULT_UPLOAD_QUEUE_SIZE,
                 lru_size=obnamlib.DEFAULT_LRU_SIZE,
                 idpath_depth=obnamlib.IDPATH_DEPTH,
                 idpath_bits=obnamlib.IDPATH_BITS,
                 idpath_skip=obnamlib.IDPATH_SKIP,
                 hooks=None,
                 current_time=None):

        self._real_fs = None
        self._lock_timeout = lock_timeout
        self._node_size = node_size
        self._upload_queue_size = upload_queue_size
        self._lru_size = lru_size
        self._idpath_depth = idpath_depth
        self._idpath_bits = idpath_bits
        self._idpath_skip = idpath_skip
        self._current_time = current_time or time.time

        self._setup_hooks(hooks or obnamlib.HookManager())
        self._setup_chunks()
        self._setup_file_keys()

    def _setup_hooks(self, hooks):
        self.hooks = hooks
        self.hooks.new('repository-toplevel-init')
        self.hooks.new_filter('repository-data')
        self.hooks.new('repository-add-client')

    def get_fs(self):
        return self._real_fs

    def set_fs(self, fs):
        self._real_fs = fs
        self._fs = HookedFS(self, fs, self.hooks)
        self._lockmgr = obnamlib.LockManager(self._fs, self._lock_timeout, '')
        self._setup_client_list()
        self._setup_client()
        self._setup_chunk_indexes()

    def init_repo(self):
        # There is nothing else to be done.
        pass

    def close(self):
        if self._real_fs:
            self._real_fs.close()

    # Client list handling.

    def _setup_client_list(self):
        self._got_client_list_lock = False
        self._added_clients = []
        self._client_list = obnamlib.ClientList(
            self._fs, self._node_size, self._upload_queue_size,
            self._lru_size, self)

    def _raw_lock_client_list(self):
        if self._got_client_list_lock:
            raise obnamlib.RepositoryClientListLockingFailed()
        self._lockmgr.lock(['.'])
        self._got_client_list_lock = True
        self._client_list.start_changes()

    def _raw_unlock_client_list(self):
        if not self._got_client_list_lock:
            raise obnamlib.RepositoryClientListNotLocked()
        self._lockmgr.unlock(['.'])
        self._setup_client_list()

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
        for client_name in self._added_clients:
            self.hooks.call(
                'repository-add-client', self._client_list, client_name)
        self._added_clients = []
        self._client_list.commit()
        self._raw_unlock_client_list()

    def force_client_list_lock(self):
        tracing.trace('forcing client list lock')
        lock_name = os.path.join('lock')
        if self._real_fs.exists(lock_name):
            self._real_fs.remove(lock_name)
        self._setup_client_list()

    def get_client_names(self):
        return self._client_list.list_clients()

    def add_client(self, client_name):
        self._require_client_list_lock()
        if self._client_list.get_client_id(client_name):
            raise obnamlib.RepositoryClientAlreadyExists(client_name)
        self._client_list.add_client(client_name)
        self._added_clients.append(client_name)

    def remove_client(self, client_name):
        self._require_client_list_lock()
        if not self._client_list.get_client_id(client_name):
            raise obnamlib.RepositoryClientDoesNotExist(client_name)
        self._client_list.remove_client(client_name)

    def rename_client(self, old_client_name, new_client_name):
        self._require_client_list_lock()

        client_names = self.get_client_names()
        if old_client_name not in client_names:
            raise obnamlib.RepositoryClientDoesNotExist(old_client_name)
        if new_client_name in client_names:
            raise obnamlib.RepositoryClientAlreadyExists(new_client_name)

        client_id = self._get_client_id(old_client_name)
        new_key = self._client_list.key(
            new_client_name, client_id, self._client_list.CLIENT_NAME)
        self._client_list.tree.insert(new_key, new_client_name)

        old_key = self._client_list.key(
            old_client_name, client_id, self._client_list.CLIENT_NAME)
        self._client_list.tree.remove(old_key)

    def get_client_encryption_key_id(self, client_name):
        client_names = self.get_client_names()
        if client_name not in client_names:
            raise obnamlib.RepositoryClientDoesNotExist(client_name)
        return self._client_list.get_client_keyid(client_name)

    def set_client_encryption_key_id(self, client_name, key_id):
        self._require_client_list_lock()
        client_names = self.get_client_names()
        if client_name not in client_names:
            raise obnamlib.RepositoryClientDoesNotExist(client_name)
        self._client_list.set_client_keyid(client_name, key_id)

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
        return self._current_time()

    def _setup_client(self):
        # We keep a list of all open clients. An open client may or
        # may not be locked. Each value in the dict is a tuple of
        # ClientMetadataTree and is_locked.
        self._open_clients = {}

    def _open_client(self, client_name):
        if client_name not in self._open_clients:
            tracing.trace('client_name=%s', client_name)
            client_id = self._get_client_id(client_name)
            if client_id is None: # pragma: no cover
                raise obnamlib.RepositoryClientDoesNotExist(client_name)

            client_dir = self._get_client_dir(client_id)
            client = obnamlib.ClientMetadataTree(
                self._fs, client_dir, self._node_size,
                    self._upload_queue_size, self._lru_size, self)
            client.init_forest()

            self._open_clients[client_name] = _OpenClient(client)

        return self._open_clients[client_name].client

    def _get_client_dir(self, client_id):
        '''Return name of sub-directory for a given client.'''
        return str(client_id)

    def _client_is_locked_by_us(self, client_name):
        if client_name in self._open_clients:
            open_client = self._open_clients[client_name]
            return open_client.locked
        return False

    def _require_client_lock(self, client_name):
        if client_name not in self.get_client_names():
            raise obnamlib.RepositoryClientDoesNotExist(client_name)
        if not self._client_is_locked_by_us(client_name):
            raise obnamlib.RepositoryClientNotLocked(client_name)

    def _raw_lock_client(self, client_name):
        tracing.trace('client_name=%s', client_name)

        if self._client_is_locked_by_us(client_name):
            raise obnamlib.RepositoryClientLockingFailed(client_name)

        client_id = self._get_client_id(client_name)
        if client_id is None: # pragma: no cover
            raise obnamlib.RepositoryClientDoesNotExist(client_name)

        # Create and initialise the client's own directory, if needed.
        client_dir = self._get_client_dir(client_id)
        if not self._fs.exists(client_dir):
            self._fs.mkdir(client_dir)
            self.hooks.call('repository-toplevel-init', self, client_dir)

        # Actually lock the directory.
        self._lockmgr.lock([client_dir])

        # Remember that we have the lock.
        self._open_client(client_name) # Ensure client is open
        open_client = self._open_clients[client_name]
        open_client.locked = True

    def _raw_unlock_client(self, client_name):
        tracing.trace('client_name=%s', client_name)
        open_client = self._open_clients[client_name]
        self._lockmgr.unlock([open_client.client.dirname])
        del self._open_clients[client_name]

    def client_is_locked(self, client_name):
        logging.info('Checking if %s is locked' % client_name)
        client = self._open_client(client_name)
        return self._lockmgr.is_locked(client.dirname)

    def lock_client(self, client_name):
        logging.info('Locking client %s' % client_name)
        self._raw_lock_client(client_name)

    def unlock_client(self, client_name):
        logging.info('Unlocking client %s' % client_name)
        self._require_client_lock(client_name)
        self._raw_unlock_client(client_name)

    def force_client_lock(self, client_name):
        logging.info('Forcing client lock open for %s', client_name)
        self._open_client(client_name)
        open_client = self._open_clients[client_name]
        lock_name = os.path.join(open_client.client.dirname, 'lock')
        if self._real_fs.exists(lock_name):
            self._real_fs.remove(lock_name)
        del self._open_clients[client_name]

    def commit_client(self, client_name):
        tracing.trace('client_name=%s', client_name)
        self._require_client_lock(client_name)

        open_client = self._open_clients[client_name]

        if open_client.removed_generation_numbers:
            self._remove_chunks_from_removed_generations(
                client_name, open_client.client,
                open_client.removed_generation_numbers)
            open_client.client.start_changes(create_tree=False)
            for gen_number in open_client.removed_generation_numbers:
                open_client.client.remove_generation(gen_number)

        if (open_client.current_generation_number or 
            open_client.removed_generation_numbers):
            open_client.client.commit()

        self._raw_unlock_client(client_name)

    def _remove_chunks_from_removed_generations(
        self, client_name, client, remove_gen_nos):

        def find_chunkids_in_gens(gen_nos):
            chunkids = set()
            for gen_number in gen_nos:
                x = client.list_chunks_in_generation(gen_number)
                chunkids = chunkids.union(set(x))
            return chunkids

        def find_gens_to_keep():
            return [gen_number
                    for gen_number in client.list_generations()
                    if gen_number not in remove_gen_nos]

        def remove_chunks(chunk_ids): # pragma: no cover
            for chunk_id in chunk_ids:
                try:
                    checksum = self._chunklist.get_checksum(chunk_id)
                except KeyError:
                    # No checksum, therefore it can't be shared, therefore
                    # we can remove it.
                    # FIXME: shouldn't this be: no checksum, so we DON'T
                    # KNOW if it's safe to remove. Actually, there's
                    # no guarantee a chunk can be removed, if we ever
                    # allow a chunk to not be in the checksum trees. Hmm.
                    self.remove_chunk(chunk_id)
                else:
                    self.remove_chunk_from_indexes(chunk_id, client_name)
                    if not self._chunksums.chunk_is_used(checksum, chunk_id):
                        self.remove_chunk(chunk_id)

        keep_gen_nos = find_gens_to_keep()
        keep_chunkids = find_chunkids_in_gens(keep_gen_nos)
        maybe_remove_chunkids = find_chunkids_in_gens(remove_gen_nos)
        remove_chunkids = maybe_remove_chunkids.difference(keep_chunkids)
        remove_chunks(remove_chunkids)

    def get_allowed_client_keys(self):
        return []

    def get_client_key(self, client_name, key): # pragma: no cover
        raise obnamlib.RepositoryClientKeyNotAllowed(
            self.format, client_name, key)

    def set_client_key(self, client_name, key, value):
        raise obnamlib.RepositoryClientKeyNotAllowed(
            self.format, client_name, key)

    def get_client_generation_ids(self, client_name):
        client = self._open_client(client_name)
        open_client = self._open_clients[client_name]
        return [
            (client_name, gen_number)
            for gen_number in client.list_generations()
            if gen_number not in open_client.removed_generation_numbers]

    def create_generation(self, client_name):
        tracing.trace('client_name=%s', client_name)
        self._require_client_lock(client_name)

        open_client = self._open_clients[client_name]
        if open_client.current_generation_number is not None:
            raise obnamlib.RepositoryClientGenerationUnfinished(client_name)

        open_client.client.start_generation()
        open_client.current_generation_number = \
            open_client.client.get_generation_id(open_client.client.tree)

        return (client_name, open_client.current_generation_number)

    # Generations for a client.

    def _require_existing_generation(self, generation_id):
        client_name, gen_number = generation_id
        if generation_id not in self.get_client_generation_ids(client_name):
            raise obnamlib.RepositoryGenerationDoesNotExist(client_name)

    def get_allowed_generation_keys(self):
        return [
            obnamlib.REPO_GENERATION_TEST_KEY,
            obnamlib.REPO_GENERATION_STARTED,
            obnamlib.REPO_GENERATION_ENDED,
            obnamlib.REPO_GENERATION_IS_CHECKPOINT,
            obnamlib.REPO_GENERATION_FILE_COUNT,
            obnamlib.REPO_GENERATION_TOTAL_DATA,
            ]

    def get_generation_key(self, generation_id, key): # pragma: no cover
        client_name, gen_number = generation_id
        client = self._open_client(client_name)

        if key == obnamlib.REPO_GENERATION_STARTED:
            started, ended = client.get_generation_times(gen_number)
            return started or 0
        elif key == obnamlib.REPO_GENERATION_ENDED:
            started, ended = client.get_generation_times(gen_number)
            return ended or 0
        elif key == obnamlib.REPO_GENERATION_IS_CHECKPOINT:
            return client.get_is_checkpoint(gen_number) or 0
        elif key == obnamlib.REPO_GENERATION_FILE_COUNT:
            return client.get_generation_file_count(gen_number) or 0
        elif key == obnamlib.REPO_GENERATION_TOTAL_DATA:
            return client.get_generation_data(gen_number) or 0
        elif key == obnamlib.REPO_GENERATION_TEST_KEY:
            return client.get_generation_test_data() or ''
        else:
            raise obnamlib.RepositoryGenerationKeyNotAllowed(
                self.format, client_name, key)

    def set_generation_key(self, generation_id, key, value): # pragma: no cover
        # FIXME: This no worky for generations other than the currently
        # started one. There should at least be an assert about it.

        client_name, gen_number = generation_id
        self._require_client_lock(client_name)
        client = self._open_client(client_name)

        if key == obnamlib.REPO_GENERATION_STARTED:
            client.set_generation_started(value)
        elif key == obnamlib.REPO_GENERATION_ENDED:
            client.set_generation_ended(value)
        elif key == obnamlib.REPO_GENERATION_IS_CHECKPOINT:
            client.set_current_generation_is_checkpoint(value)
        elif key == obnamlib.REPO_GENERATION_FILE_COUNT:
            client.set_generation_file_count(gen_number, value)
        elif key == obnamlib.REPO_GENERATION_TOTAL_DATA:
            client.set_generation_total_data(gen_number, value)
        elif key == obnamlib.REPO_GENERATION_TEST_KEY:
            client.set_generation_test_data(value)
        else:
            raise obnamlib.RepositoryGenerationKeyNotAllowed(
                self.format, client_name, key)

    def interpret_generation_spec(self, client_name, genspec):
        ids = self.get_client_generation_ids(client_name)
        if not ids:
            raise obnamlib.RepositoryClientHasNoGenerations(client_name)
        if genspec == 'latest':
            return ids[-1]
        for gen_id in ids:
            if str(gen_id[1]) == genspec:
                return gen_id
        raise obnamlib.RepositoryGenerationDoesNotExist(client_name)

    def make_generation_spec(self, gen_id):
        return str(gen_id[1])

    def remove_generation(self, gen_id):
        tracing.trace('gen_id=%s' % repr(gen_id))
        client_name, gen_number = gen_id
        self._require_client_lock(client_name)
        self._require_existing_generation(gen_id)
        open_client = self._open_clients[client_name]
        if gen_number == open_client.current_generation_number:
            open_client.current_generation = None
        open_client.removed_generation_numbers.append(gen_number)

    def get_generation_chunk_ids(self, generation_id):
        client_name, gen_number = generation_id
        client = self._open_client(client_name)
        return client.list_chunks_in_generation(gen_number)

    # Chunks and chunk indexes.

    def _setup_chunks(self):
        self._prev_chunk_id = None
        self._chunk_idpath = larch.IdPath(
            'chunks', self._idpath_depth, self._idpath_bits,
            self._idpath_skip)

    def _chunk_filename(self, chunk_id):
        return self._chunk_idpath.convert(chunk_id)

    def _random_chunk_id(self):
        return random.randint(0, obnamlib.MAX_ID)

    def put_chunk_content(self, data):
        if self._prev_chunk_id is None:
            self._prev_chunk_id = self._random_chunk_id()

        while True:
            chunk_id = (self._prev_chunk_id + 1) % obnamlib.MAX_ID
            filename = self._chunk_filename(chunk_id)
            try:
                self._fs.write_file(filename, data)
            except OSError, e: # pragma: no cover
                if e.errno == errno.EEXIST:
                    self._prev_chunk_id = self._random_chunk_id()
                    continue
                raise
            else:
                tracing.trace('chunkid=%s', chunk_id)
                break

        self._prev_chunk_id = chunk_id
        return chunk_id

    def get_chunk_content(self, chunk_id):
        try:
            return self._fs.cat(self._chunk_filename(chunk_id))
        except IOError, e:
            if e.errno == errno.ENOENT:
                raise obnamlib.RepositoryChunkDoesNotExist(str(chunk_id))
            raise # pragma: no cover

    def has_chunk(self, chunk_id):
        return self._fs.exists(self._chunk_filename(chunk_id))

    def remove_chunk(self, chunk_id):
        tracing.trace('chunk_id=%s', chunk_id)
        filename = self._chunk_filename(chunk_id)
        try:
            self._fs.remove(filename)
        except OSError:
            raise obnamlib.RepositoryChunkDoesNotExist(str(chunk_id))

    # Chunk indexes.

    def _checksum(self, data):
        return hashlib.md5(data).hexdigest()

    def _setup_chunk_indexes(self):
        self._got_chunk_indexes_lock = False
        self._chunklist = obnamlib.ChunkList(
            self._fs, self._node_size, self._upload_queue_size,
            self._lru_size, self)
        self._chunksums = obnamlib.ChecksumTree(
            self._fs, 'chunksums',  len(self._checksum('')), self._node_size,
            self._upload_queue_size, self._lru_size, self)

    def _chunk_index_dirs_to_lock(self):
        return [
            self._chunklist.dirname,
            self._chunksums.dirname,
            self._chunk_idpath.dirname]

    def _require_chunk_indexes_lock(self):
        if not self._got_chunk_indexes_lock:
            raise obnamlib.RepositoryChunkIndexesNotLocked()

    def _raw_lock_chunk_indexes(self):
        if self._got_chunk_indexes_lock:
            raise obnamlib.RepositoryChunkIndexesLockingFailed()

        self._lockmgr.lock(self._chunk_index_dirs_to_lock())
        self._got_chunk_indexes_lock = True

        tracing.trace('starting changes in chunksums and chunklist')
        self._chunksums.start_changes()
        self._chunklist.start_changes()

        # Initialize the chunks directory for encryption, etc, if it just
        # got created.
        dirname = self._chunk_idpath.dirname
        filenames = self._fs.listdir(dirname)
        if filenames == [] or filenames == ['lock']:
            self.hooks.call('repository-toplevel-init', self, dirname)

    def _raw_unlock_chunk_indexes(self):
        self._require_chunk_indexes_lock()
        self._lockmgr.unlock(self._chunk_index_dirs_to_lock())
        self._setup_chunk_indexes()

    def lock_chunk_indexes(self):
        tracing.trace('locking chunk indexes')
        self._raw_lock_chunk_indexes()

    def unlock_chunk_indexes(self):
        tracing.trace('unlocking chunk indexes')
        self._raw_unlock_chunk_indexes()

    def force_chunk_indexes_lock(self):
        tracing.trace('forcing chunk indexes lock')
        lock_name = os.path.join('lock')
        for dirname in self._chunk_index_dirs_to_lock():
            lock_name = os.path.join(dirname, 'lock')
            if self._real_fs.exists(lock_name):
                self._real_fs.remove(lock_name)
        self._setup_chunk_indexes()

    def commit_chunk_indexes(self):
        tracing.trace('committing chunk indexes')
        self._require_chunk_indexes_lock()
        self._chunklist.commit()
        self._chunksums.commit()
        self._raw_unlock_chunk_indexes()

    def put_chunk_into_indexes(self, chunk_id, data, client_name):
        tracing.trace('chunk_id=%s', chunk_id)
        checksum = self._checksum(data)
        tracing.trace('checksum of data: %s', checksum)
        tracing.trace('client_name=%s', client_name)
        client_id = self._get_client_id(client_name)
        tracing.trace('client_id=%s', client_id)

        self._require_chunk_indexes_lock()
        self._chunklist.add(chunk_id, checksum)
        self._chunksums.add(checksum, chunk_id, client_id)

    def remove_chunk_from_indexes(self, chunk_id, client_name):
        tracing.trace('chunk_id=%s', chunk_id)
        tracing.trace('client_name=%s', client_name)
        client_id = self._get_client_id(client_name)
        tracing.trace('client_id=%s', client_id)

        self._require_chunk_indexes_lock()
        checksum = self._chunklist.get_checksum(chunk_id)
        self._chunksums.remove(checksum, chunk_id, client_id)
        self._chunklist.remove(chunk_id)

    def find_chunk_id_by_content(self, data):
        checksum = self._checksum(data)
        candidates = self._chunksums.find(checksum)
        for chunk_id in candidates:
            chunk_data = self.get_chunk_content(chunk_id)
            if chunk_data == data:
                return chunk_id
        raise obnamlib.RepositoryChunkContentNotInIndexes()

    # Individual files in a generation.

    def _setup_file_keys(self):
        # Set up a mapping table between file keys and obnamlib.Metadata
        # field names. This simplifies code (at the cost of a little
        # magic) in the file key getting and setting code.
        self._file_keys = {
            obnamlib.REPO_FILE_TEST_KEY: 'target',
            obnamlib.REPO_FILE_MODE: 'st_mode',
            obnamlib.REPO_FILE_MTIME_SEC: 'st_mtime_sec',
            obnamlib.REPO_FILE_MTIME_NSEC: 'st_mtime_nsec',
            obnamlib.REPO_FILE_ATIME_SEC: 'st_atime_sec',
            obnamlib.REPO_FILE_ATIME_NSEC: 'st_atime_nsec',
            obnamlib.REPO_FILE_NLINK: 'st_nlink',
            obnamlib.REPO_FILE_SIZE: 'st_size',
            obnamlib.REPO_FILE_UID: 'st_uid',
            obnamlib.REPO_FILE_USERNAME: 'username',
            obnamlib.REPO_FILE_GID: 'st_gid',
            obnamlib.REPO_FILE_GROUPNAME: 'groupname',
            obnamlib.REPO_FILE_SYMLINK_TARGET: 'target',
            obnamlib.REPO_FILE_XATTR_BLOB: 'xattr',
            obnamlib.REPO_FILE_BLOCKS: 'st_blocks',
            obnamlib.REPO_FILE_DEV: 'st_dev',
            obnamlib.REPO_FILE_INO: 'st_ino',
            obnamlib.REPO_FILE_MD5: 'md5',
            
            }

    def _require_existing_file(self, generation_id, filename):
        client_name, gen_number = generation_id

        if generation_id not in self.get_client_generation_ids(client_name):
            raise obnamlib.RepositoryGenerationDoesNotExist(client_name)

        if not self.file_exists(generation_id, filename):
            raise obnamlib.RepositoryFileDoesNotExistInGeneration(
                client_name, self.make_generation_spec(generation_id),
                filename)

    def file_exists(self, generation_id, filename):
        client_name, gen_number = generation_id
        client = self._open_client(client_name)
        try:
            client.get_metadata(gen_number, filename)
            return True
        except KeyError:
            return False

    def add_file(self, generation_id, filename):
        client_name, gen_number = generation_id
        self._require_client_lock(client_name)
        client = self._open_client(client_name)
        encoded_metadata = obnamlib.encode_metadata(obnamlib.Metadata())
        client.create(filename, encoded_metadata)

    def remove_file(self, generation_id, filename):
        client_name, gen_number = generation_id
        self._require_client_lock(client_name)
        client = self._open_client(client_name)
        client.remove(filename) # FIXME: Only removes from unfinished gen!

    def get_allowed_file_keys(self):
        return self._file_keys.keys()

    def get_file_key(self, generation_id, filename, key):
        self._require_existing_file(generation_id, filename)

        client_name, gen_number = generation_id
        client = self._open_client(client_name)

        encoded_metadata = client.get_metadata(gen_number, filename)
        metadata = obnamlib.decode_metadata(encoded_metadata)

        if key in self._file_keys:
            value = getattr(metadata, self._file_keys[key])
            if key in obnamlib.REPO_FILE_INTEGER_KEYS:
                return value or 0
            else:
                return value or ''
        else:
            raise obnamlib.RepositoryFileKeyNotAllowed(
                self.format, client_name, key)

    def set_file_key(self, generation_id, filename, key, value):
        client_name, gen_number = generation_id
        self._require_client_lock(client_name)
        self._require_existing_file(generation_id, filename)

        client = self._open_client(client_name)

        encoded_metadata = client.get_metadata(gen_number, filename)
        metadata = obnamlib.decode_metadata(encoded_metadata)

        if key in self._file_keys:
            setattr(metadata, self._file_keys[key], value)
        else:
            raise obnamlib.RepositoryFileKeyNotAllowed(
                self.format, client_name, key)

        encoded_metadata = obnamlib.encode_metadata(metadata)
        # FIXME: Only sets in unfinished generation
        client.set_metadata(filename, encoded_metadata)

    def get_file_chunk_ids(self, generation_id, filename):
        self._require_existing_file(generation_id, filename)
        client_name, gen_number = generation_id
        client = self._open_client(client_name)
        return client.get_file_chunks(gen_number, filename)

    def clear_file_chunk_ids(self, generation_id, filename):
        self._require_existing_file(generation_id, filename)
        client_name, gen_number = generation_id
        self._require_client_lock(client_name)
        client = self._open_client(client_name)
        client.set_file_chunks(filename, []) # FIXME: current gen only

    def append_file_chunk_id(self, generation_id, filename, chunk_id):
        self._require_existing_file(generation_id, filename)
        client_name, gen_number = generation_id
        self._require_client_lock(client_name)
        client = self._open_client(client_name)
        client.append_file_chunks(filename, [chunk_id]) # FIXME: curgen only

    def get_file_children(self, generation_id, filename):
        self._require_existing_file(generation_id, filename)
        client_name, gen_number = generation_id
        client = self._open_client(client_name)
        return [os.path.join(filename, basename)
                for basename in client.listdir(gen_number, filename)]

    # Fsck.

    def get_fsck_work_item(self):
        return []
