# Copyright 2013-2015  Lars Wirzenius
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


import copy
import hashlib
import errno
import os
import random
import StringIO

import tracing
import yaml

import obnamlib


class ToplevelIsFileError(obnamlib.ObnamError):

    msg = 'File at repository root: {filename}'


class SimpleData(object):

    def __init__(self):
        self._fs = None
        self._data_name = None
        self._obj_is_loaded = False
        self._obj = {}

    def set_fs(self, fs):
        self._fs = fs

    def set_data_pathname(self, data_name):
        self._data_name = data_name

    def load(self):
        if not self._obj_is_loaded and self._fs.exists(self._data_name):
            data = self._fs.cat(self._data_name)
            self._obj = yaml.safe_load(StringIO.StringIO(data))

        # We always mark _obj as loaded so that if the file appears
        # later, that doesn't cause any changes to _obj to
        # mysteriously disappear.
        self._obj_is_loaded = True

    def save(self):
        data = yaml.safe_dump(self._obj)
        self._fs.overwrite_file(self._data_name, data)

    def clear(self):
        self._obj = {}
        self._obj_is_loaded = False

    def __getitem__(self, key):
        self.load()
        return self._obj[key]

    def __setitem__(self, key, value):
        self.load()
        self._obj[key] = value

    def get(self, key, default=None):
        self.load()
        return self._obj.get(key, default)

    def __contains__(self, key):
        self.load()
        return key in self._obj


class SimpleToplevel(object):

    def __init__(self):
        self._data = SimpleData()
        self._dirname = None

    def set_fs(self, fs):
        self._data.set_fs(fs)

    def set_dirname(self, dirname):
        self._dirname = dirname
        self._data.set_data_pathname(os.path.join(dirname, 'data.yaml'))

    def get_dirname(self):
        return self._dirname

    def clear(self):
        self._data.clear()


class SimpleClientList(SimpleToplevel):

    # We store the client list in YAML as follows:
    #
    #   clients:
    #     foo: { 'encryption-key': ... }
    #
    # Above, the client name is foo.

    def __init__(self):
        SimpleToplevel.__init__(self)
        self.set_dirname('client-list')
        self._added_clients = []
        self._hooks = None

    def set_hooks(self, hooks):
        self._hooks = hooks

    def commit(self):
        tracing.trace('client list: %r', self._data._obj)
        for client_name in self._added_clients:
            self._hooks.call('repository-add-client', self, client_name)
        self._data.save()
        self._added_clients = []
        
    def get_client_names(self):
        return self._data.get('clients', {}).keys()

    def get_client_dirname(self, client_name):
        return client_name

    def add_client(self, client_name):
        self._require_client_does_not_exist(client_name)

        clients = self._data.get('clients', {})
        clients[client_name] = {
            'encryption-key': None,
        }
        self._data['clients'] = clients

        self._added_clients.append(client_name)
        
    def remove_client(self, client_name):
        self._require_client_exists(client_name)

        clients = self._data.get('clients', {})
        del clients[client_name]
        self._data['clients'] = clients

        if client_name in self._added_clients:
            self._added_clients.remove(client_name)

    def rename_client(self, old_client_name, new_client_name):
        self._require_client_exists(old_client_name)
        self._require_client_does_not_exist(new_client_name)

        clients = self._data.get('clients', {})
        clients[new_client_name] = clients[old_client_name]
        del clients[old_client_name]
        self._data['clients'] = clients

        if old_client_name in self._added_clients: # pragma: no cover
            self._added_clients.remove(old_client_name)
        self._added_clients.append(new_client_name)

    def _require_client_exists(self, client_name):
        if client_name not in self._data.get('clients', {}):
            raise obnamlib.RepositoryClientDoesNotExist(
                client_name=client_name)

    def _require_client_does_not_exist(self, client_name):
        if client_name in self._data.get('clients', {}):
            raise obnamlib.RepositoryClientAlreadyExists(
                client_name=client_name)

    def get_client_encryption_key_id(self, client_name):
        self._require_client_exists(client_name)
        return self._data['clients'][client_name]['encryption-key']

    def set_client_encryption_key_id(self, client_name, encryption_key):
        tracing.trace('client_name=%s', client_name)
        tracing.trace('encryption_key=%s', encryption_key)
        self._require_client_exists(client_name)
        self._data['clients'][client_name]['encryption-key'] = encryption_key


class SimpleClient(SimpleToplevel):

    # We store the client data in YAML as:
    #
    #   {
    #       'generations': [
    #           {
    #               'id': '123',
    #               'keys': { ... },
    #               ...
    #               'files': {
    #                   '/': { 'keys': { ...}, 'chunks': [...] },
    #                   '/home': { ... },
    #                   '/home/liw': { ... },
    #               },
    #           }
    #       ]
    #   }

    def __init__(self, client_name):
        SimpleToplevel.__init__(self)
        self._client_name = client_name
        self._current_time = None

    def set_current_time(self, current_time):
        self._current_time = current_time

    def commit(self):
        self._finish_current_generation_if_any()
        self._data.save()

    def _finish_current_generation_if_any(self):
        generations = self._data.get('generations', [])
        if generations:
            keys = generations[-1]['keys']
            key_name = obnamlib.repo_key_name(obnamlib.REPO_GENERATION_ENDED)
            if keys[key_name] is None:
                keys[key_name] = int(self._current_time())

    def get_client_generation_ids(self):
        generations = self._data.get('generations', [])
        return [
            obnamlib.GenerationId(self._client_name, gen['id'])
            for gen in generations]

    def create_generation(self):
        self._require_previous_generation_is_finished()

        generations = self._data.get('generations', [])
        if generations:
            previous = copy.deepcopy(generations[-1])
        else:
            previous = {
                'keys': {},
                'files': {},
            }

        new_generation = dict(previous)
        new_generation['id'] = self._new_generation_number()
        keys = new_generation['keys']
        keys[obnamlib.repo_key_name(obnamlib.REPO_GENERATION_STARTED)] = \
            int(self._current_time())
        keys[obnamlib.repo_key_name(obnamlib.REPO_GENERATION_ENDED)] = None

        self._data['generations'] = generations + [new_generation]

        return obnamlib.GenerationId(self._client_name, new_generation['id'])

    def _require_previous_generation_is_finished(self):
        generations = self._data.get('generations', [])
        if generations:
            keys = generations[-1]['keys']
            key_name = obnamlib.repo_key_name(obnamlib.REPO_GENERATION_ENDED)
            if keys[key_name] is None:
                raise obnamlib.RepositoryClientGenerationUnfinished(
                    client_name=self._client_name)

    def _new_generation_number(self):
        generations = self._data.get('generations', [])
        ids = [int(gen['id']) for gen in generations]
        if ids:
            newest_id = ids[-1]
            next_id = newest_id + 1
        else:
            next_id = 1
        return str(next_id)

    def remove_generation(self, gen_number):
        generations = self._data.get('generations', [])
        remaining = []
        removed = False

        for generation in generations:
            if generation['id'] == gen_number:
                removed = True
            else:
                remaining.append(generation)

        if not removed:
            raise obnamlib.RepositoryGenerationDoesNotExist(
                client_name=self._client_name,
                gen_id=gen_number)

        self._data['generations'] = remaining

    def get_generation_key(self, gen_number, key):
        generation = self._lookup_generation_by_gen_number(gen_number)
        key_name = obnamlib.repo_key_name(key)
        if key in obnamlib.REPO_GENERATION_INTEGER_KEYS:
            value = generation['keys'].get(key_name, None)
            if value is None:
                value = 0
            return int(value)
        else:
            return generation['keys'].get(key_name, '')

    def _lookup_generation_by_gen_number(self, gen_number):
        if 'generations' in self._data:
            generations = self._data['generations']
            for generation in generations:
                if generation['id'] == gen_number:
                    return generation
        raise obnamlib.RepositoryGenerationDoesNotExist(
            gen_id=gen_number, client_name=self._client_name)

    def set_generation_key(self, gen_number, key, value):
        generation = self._lookup_generation_by_gen_number(gen_number)
        generation['keys'][obnamlib.repo_key_name(key)] = value

    def file_exists(self, gen_number, filename):
        try:
            generation = self._lookup_generation_by_gen_number(gen_number)
        except obnamlib.RepositoryGenerationDoesNotExist:
            return False
        return filename in generation['files']

    def add_file(self, gen_number, filename):
        generation = self._lookup_generation_by_gen_number(gen_number)
        if filename not in generation['files']:
            generation['files'][filename] = {
                'keys': {},
                'chunks': [],
            }

    def remove_file(self, gen_number, filename):
        generation = self._lookup_generation_by_gen_number(gen_number)
        if filename in generation['files']:
            del generation['files'][filename]

    def get_file_key(self, gen_number, filename, key):
        self._require_file_exists(gen_number, filename)
        generation = self._lookup_generation_by_gen_number(gen_number)
        files = generation['files']
        key_name = obnamlib.repo_key_name(key)

        if key in obnamlib.REPO_FILE_INTEGER_KEYS:
            default = 0
        else:
            default = ''

        if key_name not in files[filename]['keys']:
            return default
        return files[filename]['keys'][key_name] or default

    def _require_file_exists(self, gen_number, filename):
        generation = self._lookup_generation_by_gen_number(gen_number)
        if filename not in generation['files']:
            raise obnamlib.RepositoryFileDoesNotExistInGeneration(
                client_name=self._client_name,
                genspec=gen_number,
                filename=filename)

    def set_file_key(self, gen_number, filename, key, value):
        self._require_file_exists(gen_number, filename)
        generation = self._lookup_generation_by_gen_number(gen_number)
        files = generation['files']
        key_name = obnamlib.repo_key_name(key)
        files[filename]['keys'][key_name] = value

    def get_file_chunk_ids(self, gen_number, filename):
        self._require_file_exists(gen_number, filename)
        generation = self._lookup_generation_by_gen_number(gen_number)
        return generation['files'][filename]['chunks']

    def append_file_chunk_id(self, gen_number, filename, chunk_id):
        self._require_file_exists(gen_number, filename)
        generation = self._lookup_generation_by_gen_number(gen_number)
        generation['files'][filename]['chunks'].append(chunk_id)

    def clear_file_chunk_ids(self, gen_number, filename):
        self._require_file_exists(gen_number, filename)
        generation = self._lookup_generation_by_gen_number(gen_number)
        generation['files'][filename]['chunks'] = []

    def get_generation_chunk_ids(self, gen_number):
        chunk_ids = set()
        generation = self._lookup_generation_by_gen_number(gen_number)
        for filename in generation['files']:
            file_chunk_ids = generation['files'][filename]['chunks']
            chunk_ids = chunk_ids.union(set(file_chunk_ids))
        return list(chunk_ids)

    def get_file_children(self, gen_number, filename):
        self._require_file_exists(gen_number, filename)
        generation = self._lookup_generation_by_gen_number(gen_number)
        return [
            x for x in generation['files']
            if self._is_direct_child_of(x, filename)]

    def _is_direct_child_of(self, child, parent):
        return os.path.dirname(child) == parent and child != parent


class SimpleChunkStore(object):

    def __init__(self):
        self._fs = None
        self._dirname = 'chunk-store'

    def set_fs(self, fs):
        self._fs = fs

    def put_chunk_content(self, content):
        self._fs.create_and_init_toplevel(self._dirname)
        while True:
            chunk_id = self._random_chunk_id()
            filename = self._chunk_filename(chunk_id)
            try:
                self._fs.write_file(filename, content)
            except OSError, e: # pragma: no cover
                if e.errno == errno.EEXIST:
                    continue
                raise
            else:
                tracing.trace('new chunk_id=%s', chunk_id)
                return chunk_id

    def get_chunk_content(self, chunk_id):
        filename = self._chunk_filename(chunk_id)
        if not self._fs.exists(filename):
            raise obnamlib.RepositoryChunkDoesNotExist(
                chunk_id=chunk_id,
                filename=filename)
        return self._fs.cat(filename)

    def has_chunk(self, chunk_id):
        filename = self._chunk_filename(chunk_id)
        return self._fs.exists(filename)

    def remove_chunk(self, chunk_id):
        filename = self._chunk_filename(chunk_id)
        if not self._fs.exists(filename):
            raise obnamlib.RepositoryChunkDoesNotExist(
                chunk_id=chunk_id,
                filename=filename)
        self._fs.remove(filename)

    def flush_chunks(self):
        pass

    def get_chunk_ids(self):
        if not self._fs.exists(self._dirname):
            return []
        basenames = self._fs.listdir(self._dirname)
        return [
            self._parse_chunk_filename(x)
            for x in basenames
            if x.endswith('.chunk')]

    def _random_chunk_id(self):
        return random.randint(0, obnamlib.MAX_ID)

    def _chunk_filename(self, chunk_id):
        return os.path.join(self._dirname, '%d.chunk' % chunk_id)

    def _parse_chunk_filename(self, filename):
        return int(filename[:-len('.chunk')])


class SimpleChunkIndexes(SimpleToplevel):

    # Yaml:
    #
    #    index:
    #    - chunk-id: ...
    #      sha512: ...
    #      client-ids:
    #      - ...
    #
    # We use sha512 for the checksum.

    def __init__(self):
        SimpleToplevel.__init__(self)
        self.set_dirname('chunk-indexes')

    def commit(self):
        self._data.save()

    def prepare_chunk_for_indexes(self, chunk_content):
        return hashlib.sha512(chunk_content).hexdigest()

    def put_chunk_into_indexes(self, chunk_id, token, client_id):
        self._prepare_data()
        self._data['index'].append({
            'chunk-id': chunk_id,
            'sha512': token,
            'client-id': client_id,
        })

    def _prepare_data(self):
        if 'index' not in self._data:
            self._data['index'] = []

    def find_chunk_ids_by_content(self, chunk_content):
        if 'index' in self._data:
            token = self.prepare_chunk_for_indexes(chunk_content)
            result = [
                record['chunk-id']
                for record in self._data['index']
                if record['sha512'] == token]
        else:
            result = []

        if not result:
            raise obnamlib.RepositoryChunkContentNotInIndexes()
        return result

    def remove_chunk_from_indexes(self, chunk_id, client_id):
        self._prepare_data()

        self._data['index'] = self._filter_out(
            self._data['index'],
            lambda x:
            x['chunk-id'] == chunk_id and x['client-id'] == client_id)

    def _filter_out(self, records, pred):
        return [record for record in records if not pred(record)]

    def remove_chunk_from_indexes_for_all_clients(self, chunk_id):
        self._prepare_data()

        self._data['index'] = self._filter_out(
            self._data['index'],
            lambda x: x['chunk-id'] == chunk_id)

    def validate_chunk_content(self, chunk_id):
        return None


class RepositoryFormatSimple(obnamlib.RepositoryDelegator):

    '''Simplistic repository format as an example.

    This class is an example of how to implement a repository format.

    '''

    format = 'simple'

    def __init__(self, **kwargs):
        obnamlib.RepositoryDelegator.__init__(self, **kwargs)
        self.set_client_list_object(SimpleClientList())
        self.set_chunk_store_object(SimpleChunkStore())
        self.set_chunk_indexes_object(SimpleChunkIndexes())
        self.set_client_factory(SimpleClient)

    def init_repo(self):
        pass

    def close(self):
        pass

    def get_fsck_work_items(self):
        return []

    def get_shared_directories(self):
        return ['client-list', 'chunk-store', 'chunk-indexes']

    #
    # Per-client methods.
    #

    def get_allowed_client_keys(self):
        return []

    def get_client_key(self, client_name, key): # pragma: no cover
        raise obnamlib.RepositoryClientKeyNotAllowed(
            format=self.format,
            client_name=client_name,
            key_name=obnamlib.repo_key_name(key))

    def set_client_key(self, client_name, key, value):
        raise obnamlib.RepositoryClientKeyNotAllowed(
            format=self.format,
            client_name=client_name,
            key_name=obnamlib.repo_key_name(key))

    def get_client_extra_data_directory(self, client_name): # pragma: no cover
        if client_name not in self.get_client_names():
            raise obnamlib.RepositoryClientDoesNotExist(
                client_name=client_name)
        return client_name

    def get_allowed_generation_keys(self):
        return [
            obnamlib.REPO_GENERATION_TEST_KEY,
            obnamlib.REPO_GENERATION_STARTED,
            obnamlib.REPO_GENERATION_ENDED,
            obnamlib.REPO_GENERATION_IS_CHECKPOINT,
            obnamlib.REPO_GENERATION_FILE_COUNT,
            obnamlib.REPO_GENERATION_TOTAL_DATA,
            ]

    def get_allowed_file_keys(self):
        return [obnamlib.REPO_FILE_TEST_KEY,
                obnamlib.REPO_FILE_MODE,
                obnamlib.REPO_FILE_MTIME_SEC,
                obnamlib.REPO_FILE_MTIME_NSEC,
                obnamlib.REPO_FILE_ATIME_SEC,
                obnamlib.REPO_FILE_ATIME_NSEC,
                obnamlib.REPO_FILE_NLINK,
                obnamlib.REPO_FILE_SIZE,
                obnamlib.REPO_FILE_UID,
                obnamlib.REPO_FILE_USERNAME,
                obnamlib.REPO_FILE_GID,
                obnamlib.REPO_FILE_GROUPNAME,
                obnamlib.REPO_FILE_SYMLINK_TARGET,
                obnamlib.REPO_FILE_XATTR_BLOB,
                obnamlib.REPO_FILE_BLOCKS,
                obnamlib.REPO_FILE_DEV,
                obnamlib.REPO_FILE_INO,
                obnamlib.REPO_FILE_MD5]

    def interpret_generation_spec(self, client_name, genspec):
        ids = self.get_client_generation_ids(client_name)
        if not ids:
            raise obnamlib.RepositoryClientHasNoGenerations(
                client_name=client_name)

        if genspec == 'latest':
            return ids[-1]

        for gen_id in ids:
            if self.make_generation_spec(gen_id) == genspec:
                return gen_id

        raise obnamlib.RepositoryGenerationDoesNotExist(
            client_name=client_name, gen_id=genspec)

    def make_generation_spec(self, generation_id):
        return generation_id.gen_number
