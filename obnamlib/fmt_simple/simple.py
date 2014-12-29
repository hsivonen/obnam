# Copyright 2013-2014  Lars Wirzenius
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
#
# =*= License: GPL-3+ =*=


import obnamlib


class KeyValueStore(object):

    def __init__(self):
        self._map = {}

    def get_value(self, key, default):
        if key in self._map:
            return self._map[key]
        return default

    def set_value(self, key, value):
        self._map[key] = value

    def remove_value(self, key):
        del self._map[key]

    def items(self):
        return self._map.items()

    def copy(self):
        other = KeyValueStore()
        for key, value in self.items():
            other.set_value(key, value)
        return other


class LockableKeyValueStore(object):

    def __init__(self):
        self.locked = False
        self.data = KeyValueStore()
        self.stashed = None

    def lock(self):
        assert not self.locked
        self.stashed = self.data
        self.data = self.data.copy()
        self.locked = True

    def unlock(self):
        assert self.locked
        self.data = self.stashed
        self.stashed = None
        self.locked = False

    def commit(self):
        assert self.locked
        self.stashed = None
        self.locked = False

    def get_value(self, key, default):
        return self.data.get_value(key, default)

    def set_value(self, key, value):
        self.data.set_value(key, value)

    def remove_value(self, key):
        self.data.remove_value(key)

    def items(self):
        return self.data.items()


class Counter(object):

    def __init__(self):
        self._latest = 0

    def next(self):
        self._latest += 1
        return self._latest


class SimpleClient(object):

    def __init__(self, name):
        self.name = name
        self.key_id = None
        self.generation_counter = Counter()
        self.data = LockableKeyValueStore()

    def is_locked(self):
        return self.data.locked

    def lock(self):
        if self.data.locked:
            raise obnamlib.RepositoryClientLockingFailed(
                client_name=self.name)
        self.data.lock()

    def _require_lock(self):
        if not self.data.locked:
            raise obnamlib.RepositoryClientNotLocked(client_name=self.name)

    def unlock(self):
        self._require_lock()
        self.data.unlock()

    def force_lock(self):
        if self.data.locked:
            self.data.unlock()

    def commit(self):
        self._require_lock()
        self.data.set_value('current-generation', None)
        self.data.commit()

    def get_key(self, key):
        return self.data.get_value(key, '')

    def set_key(self, key, value):
        self._require_lock()
        self.data.set_value(key, value)

    def get_generation_ids(self):
        key = 'generation-ids'
        return self.data.get_value(key, [])

    def create_generation(self):
        self._require_lock()
        if self.data.get_value('current-generation', None) is not None:
            raise obnamlib.RepositoryClientGenerationUnfinished(
                client_name=self.name)
        generation_id = (self.name, self.generation_counter.next())
        ids = self.data.get_value('generation-ids', [])
        self.data.set_value('generation-ids', ids + [generation_id])
        self.data.set_value('current-generation', generation_id)

        if ids:
            prev_gen_id = ids[-1]
            for key, value in self.data.items():
                if self._is_filekey(key):
                    x, gen_id, filename = key
                    if gen_id == prev_gen_id:
                        value = self.data.get_value(key, None)
                        self.data.set_value(
                            self._filekey(generation_id, filename), value)
                elif self._is_filekeykey(key):
                    x, gen_id, filename, k = key
                    if gen_id == prev_gen_id:
                        value = self.data.get_value(key, None)
                        self.data.set_value(
                            self._filekeykey(generation_id, filename, k),
                            value)
                elif self._is_filechunkskey(key):
                    x, gen_id, filename = key
                    if gen_id == prev_gen_id:
                        value = self.data.get_value(key, [])
                        self.data.set_value(
                            self._filechunkskey(generation_id, filename),
                            value)

        return generation_id

    def _require_generation(self, gen_id):
        ids = self.data.get_value('generation-ids', [])
        if gen_id not in ids:
            raise obnamlib.RepositoryGenerationDoesNotExist(
                client_name=self.name, gen_id=gen_id)

    def get_generation_key(self, gen_id, key):
        return self.data.get_value(gen_id + (key,), '')

    def set_generation_key(self, gen_id, key, value):
        self._require_lock()
        self.data.set_value(gen_id + (key,), value)

    def remove_generation(self, gen_id):
        self._require_lock()
        self._require_generation(gen_id)
        ids = self.data.get_value('generation-ids', [])
        self.data.set_value('generation-ids', [x for x in ids if x != gen_id])

    def get_generation_chunk_ids(self, gen_id):
        chunk_ids = []
        for key, value in self.data.items():
            if self._is_filechunkskey(key) and key[1] == gen_id:
                chunk_ids.extend(value)
        return chunk_ids

    def interpret_generation_spec(self, genspec):
        ids = self.data.get_value('generation-ids', [])
        if not ids:
            raise obnamlib.RepositoryClientHasNoGenerations(
                client_name=self.name)
        if genspec == 'latest':
            if ids:
                return ids[-1]
        else:
            gen_number = int(genspec)
            if (self.name, gen_number) in ids:
                return (self.name, gen_number)
        raise obnamlib.RepositoryGenerationDoesNotExist(
            client_name=self.name, gen_id=genspec)

    def make_generation_spec(self, generation_id):
        name, gen_number = generation_id
        return str(gen_number)

    def _filekey(self, gen_id, filename):
        return ('file', gen_id, filename)

    def _is_filekey(self, key):
        return (type(key) is tuple and len(key) == 3 and key[0] == 'file')

    def file_exists(self, gen_id, filename):
        return self.data.get_value(self._filekey(gen_id, filename), False)

    def add_file(self, gen_id, filename):
        self.data.set_value(self._filekey(gen_id, filename), True)

    def remove_file(self, gen_id, filename):
        keys = []
        for key, value in self.data.items():
            right_kind = (
                self._is_filekey(key) or
                self._is_filekeykey(key) or
                self._is_filechunkskey(key))
            if right_kind:
                if key[1] == gen_id and key[2] == filename:
                    keys.append(key)

        for k in keys:
            self.data.remove_value(k)

    def _filekeykey(self, gen_id, filename, key):
        return ('filekey', gen_id, filename, key)

    def _is_filekeykey(self, key):
        return (type(key) is tuple and len(key) == 4 and key[0] == 'filekey')

    def _require_file(self, gen_id, filename):
        if not self.file_exists(gen_id, filename):
            raise obnamlib.RepositoryFileDoesNotExistInGeneration(
                client_name=self.name,
                genspec=self.make_generation_spec(gen_id),
                filename=filename)

    def get_file_key(self, gen_id, filename, key):
        self._require_generation(gen_id)
        self._require_file(gen_id, filename)
        if key in obnamlib.REPO_FILE_INTEGER_KEYS:
            default = 0
        else:
            default = ''
        return self.data.get_value(
            self._filekeykey(gen_id, filename, key), default)

    def set_file_key(self, gen_id, filename, key, value):
        self._require_generation(gen_id)
        self._require_file(gen_id, filename)
        self.data.set_value(self._filekeykey(gen_id, filename, key), value)

    def _filechunkskey(self, gen_id, filename):
        return ('filechunks', gen_id, filename)

    def _is_filechunkskey(self, key):
        return (
            type(key) is tuple and len(key) == 3 and key[0] == 'filechunks')

    def get_file_chunk_ids(self, gen_id, filename):
        self._require_generation(gen_id)
        self._require_file(gen_id, filename)
        return self.data.get_value(self._filechunkskey(gen_id, filename), [])

    def append_file_chunk_id(self, gen_id, filename, chunk_id):
        self._require_generation(gen_id)
        self._require_file(gen_id, filename)
        chunk_ids = self.get_file_chunk_ids(gen_id, filename)
        self.data.set_value(
            self._filechunkskey(gen_id, filename),
            chunk_ids + [chunk_id])

    def clear_file_chunk_ids(self, gen_id, filename):
        self._require_generation(gen_id)
        self._require_file(gen_id, filename)
        self.data.set_value(self._filechunkskey(gen_id, filename), [])

    def get_file_children(self, gen_id, filename):
        children = []
        if filename.endswith('/'):
            prefix = filename
        else:
            prefix = filename + '/'
        for key, value in self.data.items():
            if not self._is_filekey(key):
                continue
            x, y, candidate = key
            if candidate == filename:
                continue
            if not candidate.startswith(prefix): # pragma: no cover
                continue
            if '/' in candidate[len(prefix):]:
                continue
            children.append(candidate)
        return children


class SimpleClientList(object):

    def __init__(self):
        self.data = LockableKeyValueStore()

    def lock(self):
        if self.data.locked:
            raise obnamlib.RepositoryClientListLockingFailed()
        self.data.lock()

    def unlock(self):
        if not self.data.locked:
            raise obnamlib.RepositoryClientListNotLocked()
        self.data.unlock()

    def commit(self):
        if not self.data.locked:
            raise obnamlib.RepositoryClientListNotLocked()
        self.data.commit()

    def force(self):
        if self.data.locked:
            self.unlock()

    def _require_lock(self):
        if not self.data.locked:
            raise obnamlib.RepositoryClientListNotLocked()

    def names(self):
        return [k for k, v in self.data.items() if v is not None]

    def __getitem__(self, client_name):
        client = self.data.get_value(client_name, None)
        if client is None:
            raise obnamlib.RepositoryClientDoesNotExist(
                client_name=client_name)
        return client

    def add(self, client_name):
        self._require_lock()
        if self.data.get_value(client_name, None) is not None:
            raise obnamlib.RepositoryClientAlreadyExists(
                client_name=client_name)
        self.data.set_value(client_name, SimpleClient(client_name))

    def remove(self, client_name):
        self._require_lock()
        if self.data.get_value(client_name, None) is None:
            raise obnamlib.RepositoryClientDoesNotExist(
                client_name=client_name)
        self.data.set_value(client_name, None)

    def rename(self, old_client_name, new_client_name):
        self._require_lock()
        client = self.data.get_value(old_client_name, None)
        if client is None:
            raise obnamlib.RepositoryClientDoesNotExist(
                client_name=old_client_name)
        if self.data.get_value(new_client_name, None) is not None:
            raise obnamlib.RepositoryClientAlreadyExists(
                client_name=new_client_name)
        self.data.set_value(old_client_name, None)
        self.data.set_value(new_client_name, client)

    def get_client_by_generation_id(self, gen_id):
        client_name, generation_number = gen_id
        return self[client_name]

    def get_client_encryption_key_id(self, client_name):
        client = self.data.get_value(client_name, None)
        if client is None:
            raise obnamlib.RepositoryClientDoesNotExist(
                client_name=client_name)
        return client.key_id

    def set_client_encryption_key_id(self, client_name, key_id):
        client = self.data.get_value(client_name, None)
        if client is None:
            raise obnamlib.RepositoryClientDoesNotExist(
                client_name=client_name)
        client.key_id = key_id


class ChunkStore(object):

    def __init__(self):
        self.next_chunk_id = Counter()
        self.chunks = {}

    def put_chunk_content(self, content):
        chunk_id = self.next_chunk_id.next()
        self.chunks[chunk_id] = content
        return chunk_id

    def get_chunk_content(self, chunk_id):
        if chunk_id not in self.chunks:
            raise obnamlib.RepositoryChunkDoesNotExist(chunk_id=str(chunk_id))
        return self.chunks[chunk_id]

    def has_chunk(self, chunk_id):
        return chunk_id in self.chunks

    def remove_chunk(self, chunk_id):
        if chunk_id not in self.chunks:
            raise obnamlib.RepositoryChunkDoesNotExist(chunk_id=str(chunk_id))
        del self.chunks[chunk_id]

    def get_chunk_ids(self):
        return self.chunks.keys()


class ChunkIndexes(object):

    def __init__(self):
        self.data = LockableKeyValueStore()

    def lock(self):
        if self.data.locked:
            raise obnamlib.RepositoryChunkIndexesLockingFailed()
        self.data.lock()

    def _require_lock(self):
        if not self.data.locked:
            raise obnamlib.RepositoryChunkIndexesNotLocked()

    def unlock(self):
        self._require_lock()
        self.data.unlock()

    def commit(self):
        self._require_lock()
        self.data.commit()

    def force(self):
        if self.data.locked:
            self.unlock()

    def prepare(self, chunk_content):
        return chunk_content

    def put_chunk(self, chunk_id, token_is_chunk_content, client_id):
        self._require_lock()
        self.data.set_value(chunk_id, token_is_chunk_content)

    def find_chunk(self, chunk_content):
        chunk_ids = []
        for chunk_id, stored_content in self.data.items():
            if stored_content == chunk_content:
                chunk_ids.append(chunk_id)
        if not chunk_ids:
            raise obnamlib.RepositoryChunkContentNotInIndexes()
        return chunk_ids

    def remove_chunk(self, chunk_id, client_id):
        self._require_lock()
        self.data.set_value(chunk_id, None)


class RepositoryFormatSimple(obnamlib.RepositoryInterface):

    '''Simplistic repository format as an example.

    This class is an example of how to implement a repository format.

    '''

    format = 'simple'

    def __init__(self, **kwargs):
        self._client_list = SimpleClientList()
        self._chunk_store = ChunkStore()
        self._chunk_indexes = ChunkIndexes()
        self._fs = None

    def get_fs(self):
        return self._fs

    def set_fs(self, fs):
        self._fs = fs

    def init_repo(self):
        pass

    def close(self):
        pass

    def get_client_names(self):
        return self._client_list.names()

    def lock_client_list(self):
        self._client_list.lock()

    def unlock_client_list(self):
        self._client_list.unlock()

    def commit_client_list(self):
        self._client_list.commit()

    def got_client_list_lock(self):
        return self._client_list.data.locked

    def force_client_list_lock(self):
        self._client_list.force()

    def add_client(self, client_name):
        self._client_list.add(client_name)

    def remove_client(self, client_name):
        self._client_list.remove(client_name)

    def rename_client(self, old_client_name, new_client_name):
        self._client_list.rename(old_client_name, new_client_name)

    def get_client_encryption_key_id(self, client_name):
        return self._client_list.get_client_encryption_key_id(client_name)

    def set_client_encryption_key_id(self, client_name, key_id):
        self._client_list.set_client_encryption_key_id(client_name, key_id)

    def client_is_locked(self, client_name):
        return self._client_list[client_name].is_locked()

    def lock_client(self, client_name):
        self._client_list[client_name].lock()

    def unlock_client(self, client_name):
        self._client_list[client_name].unlock()

    def commit_client(self, client_name):
        self._client_list[client_name].commit()

    def got_client_lock(self, client_name):
        return self._client_list[client_name].data.locked

    def force_client_lock(self, client_name):
        self._client_list[client_name].force_lock()

    def get_allowed_client_keys(self):
        return [obnamlib.REPO_CLIENT_TEST_KEY]

    def get_client_key(self, client_name, key):
        return self._client_list[client_name].get_key(key)

    def set_client_key(self, client_name, key, value):
        if key not in self.get_allowed_client_keys():
            raise obnamlib.RepositoryClientKeyNotAllowed(
                format=self.format,
                client_name=client_name,
                key_name=obnamlib.repo_key_name(key))
        self._client_list[client_name].set_key(key, value)

    def get_client_generation_ids(self, client_name):
        return self._client_list[client_name].get_generation_ids()

    def get_client_extra_data_directory(self, client_name):
        return client_name

    def create_generation(self, client_name):
        return self._client_list[client_name].create_generation()

    def get_allowed_generation_keys(self):
        return [
            obnamlib.REPO_GENERATION_TEST_KEY,
            obnamlib.REPO_GENERATION_STARTED,
            obnamlib.REPO_GENERATION_ENDED,
            ]

    def get_generation_key(self, generation_id, key):
        client = self._client_list.get_client_by_generation_id(generation_id)
        return client.get_generation_key(generation_id, key)

    def set_generation_key(self, generation_id, key, value):
        client = self._client_list.get_client_by_generation_id(generation_id)
        if key not in self.get_allowed_generation_keys():
            raise obnamlib.RepositoryGenerationKeyNotAllowed(
                format=self.format,
                client_name=client.name,
                key_name=obnamlib.repo_key_name(key))
        return client.set_generation_key(generation_id, key, value)

    def remove_generation(self, generation_id):
        client = self._client_list.get_client_by_generation_id(generation_id)
        client.remove_generation(generation_id)

    def get_generation_chunk_ids(self, generation_id):
        client = self._client_list.get_client_by_generation_id(generation_id)
        return client.get_generation_chunk_ids(generation_id)

    def interpret_generation_spec(self, client_name, genspec):
        client = self._client_list[client_name]
        return client.interpret_generation_spec(genspec)

    def make_generation_spec(self, generation_id):
        client = self._client_list.get_client_by_generation_id(generation_id)
        return client.make_generation_spec(generation_id)

    def file_exists(self, generation_id, filename):
        client = self._client_list.get_client_by_generation_id(generation_id)
        return client.file_exists(generation_id, filename)

    def add_file(self, generation_id, filename):
        client = self._client_list.get_client_by_generation_id(generation_id)
        return client.add_file(generation_id, filename)

    def remove_file(self, generation_id, filename):
        client = self._client_list.get_client_by_generation_id(generation_id)
        return client.remove_file(generation_id, filename)

    def get_file_key(self, generation_id, filename, key):
        client = self._client_list.get_client_by_generation_id(generation_id)
        if key not in self.get_allowed_file_keys():
            raise obnamlib.RepositoryFileKeyNotAllowed(
                format=self.format,
                client_name=client.name,
                key_name=obnamlib.repo_key_name(key))
        return client.get_file_key(generation_id, filename, key)

    def set_file_key(self, generation_id, filename, key, value):
        client = self._client_list.get_client_by_generation_id(generation_id)
        if key not in self.get_allowed_file_keys():
            raise obnamlib.RepositoryFileKeyNotAllowed(
                format=self.format,
                client_name=client.name,
                key_name=obnamlib.repo_key_name(key))
        client.set_file_key(generation_id, filename, key, value)

    def get_allowed_file_keys(self):
        return [
            obnamlib.REPO_FILE_TEST_KEY,
            obnamlib.REPO_FILE_MODE,
            obnamlib.REPO_FILE_MTIME_SEC,
            obnamlib.REPO_FILE_MTIME_NSEC,
            obnamlib.REPO_FILE_ATIME_SEC,
            obnamlib.REPO_FILE_ATIME_NSEC,
            obnamlib.REPO_FILE_NLINK,
            obnamlib.REPO_FILE_SIZE,
            obnamlib.REPO_FILE_UID,
            obnamlib.REPO_FILE_GID,
            obnamlib.REPO_FILE_BLOCKS,
            obnamlib.REPO_FILE_DEV,
            obnamlib.REPO_FILE_INO,
            obnamlib.REPO_FILE_USERNAME,
            obnamlib.REPO_FILE_GROUPNAME,
            obnamlib.REPO_FILE_SYMLINK_TARGET,
            obnamlib.REPO_FILE_XATTR_BLOB,
            obnamlib.REPO_FILE_MD5,
            ]

    def get_file_chunk_ids(self, generation_id, filename):
        client = self._client_list.get_client_by_generation_id(generation_id)
        return client.get_file_chunk_ids(generation_id, filename)

    def append_file_chunk_id(self, generation_id, filename, chunk_id):
        client = self._client_list.get_client_by_generation_id(generation_id)
        return client.append_file_chunk_id(generation_id, filename, chunk_id)

    def clear_file_chunk_ids(self, generation_id, filename):
        client = self._client_list.get_client_by_generation_id(generation_id)
        client.clear_file_chunk_ids(generation_id, filename)

    def get_file_children(self, generation_id, filename):
        client = self._client_list.get_client_by_generation_id(generation_id)
        return client.get_file_children(generation_id, filename)

    def put_chunk_content(self, content):
        return self._chunk_store.put_chunk_content(content)

    def get_chunk_content(self, chunk_id):
        return self._chunk_store.get_chunk_content(chunk_id)

    def has_chunk(self, chunk_id):
        return self._chunk_store.has_chunk(chunk_id)

    def remove_chunk(self, chunk_id):
        self._chunk_store.remove_chunk(chunk_id)

    def get_chunk_ids(self):
        return self._chunk_store.get_chunk_ids()

    def lock_chunk_indexes(self):
        self._chunk_indexes.lock()

    def unlock_chunk_indexes(self):
        self._chunk_indexes.unlock()

    def commit_chunk_indexes(self):
        self._chunk_indexes.commit()

    def got_chunk_indexes_lock(self):
        return self._chunk_indexes.data.locked

    def force_chunk_indexes_lock(self):
        self._chunk_indexes.force()

    def prepare_chunk_for_indexes(self, chunk_content):
        return self._chunk_indexes.prepare(chunk_content)

    def put_chunk_into_indexes(self, chunk_id, token, client_id):
        self._chunk_indexes.put_chunk(chunk_id, token, client_id)

    def find_chunk_ids_by_content(self, chunk_content):
        return self._chunk_indexes.find_chunk(chunk_content)

    def remove_chunk_from_indexes(self, chunk_id, client_id):
        return self._chunk_indexes.remove_chunk(chunk_id, client_id)

    def remove_chunk_from_indexes_for_all_clients(self, chunk_id):
        return self._chunk_indexes.remove_chunk(chunk_id, None)

    def validate_chunk_content(self, chunk_id):
        return None

    def get_fsck_work_items(self):
        return []
