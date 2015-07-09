# Copyright 2015  Lars Wirzenius
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
import os

import obnamlib


class GAClient(object):

    def __init__(self, client_name):
        self._fs = None
        self._dirname = None
        self._client_name = client_name
        self._current_time = None
        self.clear()

    def set_current_time(self, current_time):
        self._current_time = current_time

    def set_fs(self, fs):
        self._fs = fs

    def set_dirname(self, dirname):
        self._dirname = dirname

    def get_dirname(self):
        return self._dirname

    def clear(self):
        self._client_keys = GAKeys()
        self._generations = GAGenerationList()
        self._data_is_loaded = False

    def commit(self):
        self._load_data()
        self._finish_current_generation_if_any()
        self._save_data()

    def _finish_current_generation_if_any(self):
        if self._generations:
            latest = self._generations.get_latest()
            key_name = obnamlib.repo_key_name(obnamlib.REPO_GENERATION_ENDED)
            if latest.get_key(key_name) is None:
                latest.set_key(key_name, int(self._current_time()))

    def _save_data(self):
        self._save_file_metadata()
        self._save_per_client_data()

    def _save_file_metadata(self):
        for gen in self._generations:
            metadata = gen.get_file_metadata()
            gen.set_file_metadata_id(metadata.get_blob_id())

    def _get_blob_store(self):
        bag_store = obnamlib.BagStore()
        bag_store.set_location(self._fs, self._dirname)

        blob_store = obnamlib.BlobStore()
        blob_store.set_bag_store(bag_store)

        return blob_store

    def _save_per_client_data(self):
        data = {
            'keys': self._client_keys.as_dict(),
            'generations': [g.as_dict() for g in self._generations],
        }
        blob = obnamlib.serialise_object(data)
        filename = self._get_filename()
        self._fs.overwrite_file(filename, blob)

    def _load_data(self):
        if not self._data_is_loaded:
            self.clear()
            self._load_per_client_data()
            self._load_file_metadata()
            self._data_is_loaded = True

    def _load_per_client_data(self):
        filename = self._get_filename()
        if self._fs.exists(filename):
            blob = self._fs.cat(filename)
            data = obnamlib.deserialise_object(blob)
            self._client_keys.set_from_dict(data['keys'])
            for gen_dict in data['generations']:
                gen = GAGeneration()
                gen.set_from_dict(gen_dict)
                self._generations.append(gen)

    def _get_filename(self):
        return os.path.join(self.get_dirname(), 'data.dat')

    def _load_file_metadata(self):
        blob_store = self._get_blob_store()
        for gen in self._generations:
            metadata = gen.get_file_metadata()
            metadata.set_blob_store(blob_store)
            metadata.set_blob_id(gen.get_file_metadata_id())

    def get_client_generation_ids(self):
        self._load_data()
        return [
            obnamlib.GenerationId(self._client_name, gen.get_number())
            for gen in self._generations]

    def create_generation(self):
        self._load_data()
        self._require_previous_generation_is_finished()

        new_generation = GAGeneration()
        new_metadata = new_generation.get_file_metadata()
        new_metadata.set_blob_store(self._get_blob_store())

        if self._generations:
            latest = self._generations.get_latest()
            new_dict = copy.deepcopy(latest.as_dict())
            new_generation.set_from_dict(new_dict)

            latest_metadata = latest.get_file_metadata()
            new_metadata.set_blob_id(latest_metadata.get_blob_id())

        new_generation.set_number(self._new_generation_number())
        new_generation.set_key(
            obnamlib.repo_key_name(obnamlib.REPO_GENERATION_STARTED),
            int(self._current_time()))
        new_generation.set_key(
            obnamlib.repo_key_name(obnamlib.REPO_GENERATION_ENDED),
            None)

        self._generations.append(new_generation)

        return obnamlib.GenerationId(
            self._client_name, new_generation.get_number())

    def _require_previous_generation_is_finished(self):
        if self._generations:
            latest = self._generations.get_latest()
            key_name = obnamlib.repo_key_name(obnamlib.REPO_GENERATION_ENDED)
            if latest.get_key(key_name) is None:
                raise obnamlib.RepositoryClientGenerationUnfinished(
                    client_name=self._client_name)

    def _new_generation_number(self):
        if self._generations:
            ids = [gen.get_number() for gen in self._generations]
            return str(int(ids[-1]) + 1)
        else:
            return str(1)

    def remove_generation(self, gen_number):
        self._load_data()
        remaining = []
        removed = False

        for generation in self._generations:
            if generation.get_number() == gen_number:
                removed = True
            else:
                remaining.append(generation)

        if not removed:
            raise obnamlib.RepositoryGenerationDoesNotExist(
                client_name=self._client_name,
                gen_id=gen_number)

        self._generations.set_generations(remaining)

    def get_generation_key(self, gen_number, key):
        self._load_data()
        generation = self._lookup_generation_by_gen_number(gen_number)
        key_name = obnamlib.repo_key_name(key)
        if key in obnamlib.REPO_GENERATION_INTEGER_KEYS:
            value = generation.get_key(key_name)
            if value is None:
                value = 0
            return int(value)
        else:
            return generation.get_key(key_name, default='')

    def _lookup_generation_by_gen_number(self, gen_number):
        for generation in self._generations:
            if generation.get_number() == gen_number:
                return generation
        raise obnamlib.RepositoryGenerationDoesNotExist(
            gen_id=gen_number, client_name=self._client_name)

    def set_generation_key(self, gen_number, key, value):
        self._load_data()
        generation = self._lookup_generation_by_gen_number(gen_number)
        generation.set_key(obnamlib.repo_key_name(key), value)

    def file_exists(self, gen_number, filename):
        self._load_data()
        try:
            generation = self._lookup_generation_by_gen_number(gen_number)
        except obnamlib.RepositoryGenerationDoesNotExist:
            return False
        metadata = generation.get_file_metadata()
        return metadata.file_exists(filename)

    def add_file(self, gen_number, filename):
        self._load_data()
        generation = self._lookup_generation_by_gen_number(gen_number)
        metadata = generation.get_file_metadata()
        metadata.add_file(filename)

    def remove_file(self, gen_number, filename):
        self._load_data()
        generation = self._lookup_generation_by_gen_number(gen_number)
        metadata = generation.get_file_metadata()
        metadata.remove_file(filename)

    def get_file_key(self, gen_number, filename, key):
        self._load_data()
        self._require_file_exists(gen_number, filename)
        generation = self._lookup_generation_by_gen_number(gen_number)
        metadata = generation.get_file_metadata()
        key_name = obnamlib.repo_key_name(key)

        if key in obnamlib.REPO_FILE_INTEGER_KEYS:
            default = 0
        else:
            default = ''

        value = metadata.get_file_key(filename, key_name)
        if value is None:
            return default
        return value

    def _require_file_exists(self, gen_number, filename):
        generation = self._lookup_generation_by_gen_number(gen_number)
        metadata = generation.get_file_metadata()
        if not metadata.file_exists(filename):
            raise obnamlib.RepositoryFileDoesNotExistInGeneration(
                client_name=self._client_name,
                genspec=gen_number,
                filename=filename)

    def set_file_key(self, gen_number, filename, key, value):
        self._load_data()
        self._require_file_exists(gen_number, filename)
        generation = self._lookup_generation_by_gen_number(gen_number)
        metadata = generation.get_file_metadata()
        key_name = obnamlib.repo_key_name(key)
        metadata.set_file_key(filename, key_name, value)

    def get_file_chunk_ids(self, gen_number, filename):
        self._load_data()
        self._require_file_exists(gen_number, filename)
        generation = self._lookup_generation_by_gen_number(gen_number)
        metadata = generation.get_file_metadata()
        return metadata.get_file_chunk_ids(filename)

    def append_file_chunk_id(self, gen_number, filename, chunk_id):
        self._load_data()
        self._require_file_exists(gen_number, filename)
        generation = self._lookup_generation_by_gen_number(gen_number)
        metadata = generation.get_file_metadata()
        metadata.append_file_chunk_id(filename, chunk_id)

    def clear_file_chunk_ids(self, gen_number, filename):
        self._load_data()
        self._require_file_exists(gen_number, filename)
        generation = self._lookup_generation_by_gen_number(gen_number)
        metadata = generation.get_file_metadata()
        metadata.clear_file_chunk_ids(filename)

    def get_generation_chunk_ids(self, gen_number):
        self._load_data()
        chunk_ids = set()
        generation = self._lookup_generation_by_gen_number(gen_number)
        metadata = generation.get_file_metadata()
        for filename in metadata:
            file_chunk_ids = metadata.get_file_chunk_ids(filename)
            chunk_ids = chunk_ids.union(set(file_chunk_ids))
        return list(chunk_ids)

    def get_file_children(self, gen_number, filename):
        self._load_data()
        self._require_file_exists(gen_number, filename)
        generation = self._lookup_generation_by_gen_number(gen_number)
        metadata = generation.get_file_metadata()
        return [
            x for x in metadata
            if self._is_direct_child_of(x, filename)]

    def _is_direct_child_of(self, child, parent):
        return os.path.dirname(child) == parent and child != parent


class GAKeys(object):

    def __init__(self):
        self._dict = {}

    def as_dict(self):
        return self._dict

    def set_from_dict(self, keys_dict):
        self._dict = keys_dict

    def get_key(self, key, default=None):
        return self._dict.get(key, default)

    def set_key(self, key, value):
        self._dict[key] = value


class GAGenerationList(object):

    def __init__(self):
        self._generations = []

    def __len__(self):
        return len(self._generations)

    def __iter__(self):
        for gen in self._generations[:]:
            yield gen

    def get_latest(self):
        return self._generations[-1]

    def append(self, gen):
        self._generations.append(gen)

    def set_generations(self, generations):
        self._generations = generations


class GAGeneration(object):

    def __init__(self):
        self._id = None
        self._keys = GAKeys()
        self._file_metadata = GAFileMetadata()
        self._file_metadata_id = None

    def as_dict(self):
        return {
            'id': self._id,
            'keys': self._keys.as_dict(),
            'file_metadata_id': self._file_metadata_id,
        }

    def set_from_dict(self, data):
        self._id = data['id']
        self._keys = GAKeys()
        self._keys.set_from_dict(data['keys'])
        self._file_metadata_id = data['file_metadata_id']

    def get_number(self):
        return self._id

    def set_number(self, new_id):
        self._id = new_id

    def keys(self):
        return self._keys.keys()

    def get_key(self, key, default=None):
        return self._keys.get_key(key, default=default)

    def set_key(self, key, value):
        self._keys.set_key(key, value)

    def get_file_metadata_id(self):
        return self._file_metadata_id

    def set_file_metadata_id(self, metadata_id):
        self._file_metadata_id = metadata_id

    def get_file_metadata(self):
        return self._file_metadata


class GAFileMetadata(object):

    def __init__(self):
        self._blob_store = None
        self._blob_id = None

    def set_blob_store(self, blob_store):
        self._blob_store = blob_store

    def set_blob_id(self, blob_id):
        self._blob_id = blob_id

    def get_blob_id(self):
        return self._blob_id

    def _load(self):
        if self._blob_id is None:
            return {}

        blob = self._blob_store.get_blob(self._blob_id)
        return obnamlib.deserialise_object(blob)

    def _save(self, files):
        blob = obnamlib.serialise_object(files)
        self._blob_id = self._blob_store.put_blob(blob)

    def __iter__(self):
        for filename in self._load():
            yield filename

    def file_exists(self, filename):
        return filename in self._load()

    def add_file(self, filename):
        files = self._load()
        if filename not in files:
            files[filename] = {
                'keys': {},
                'chunks': [],
            }
            self._save(files)

    def remove_file(self, filename):
        files = self._load()
        if filename in files:
            del files[filename]
            self._save(files)

    def get_file_key(self, filename, key):
        files = self._load()
        return files[filename]['keys'].get(key)

    def set_file_key(self, filename, key, value):
        files = self._load()
        files[filename]['keys'][key] = value
        self._save(files)

    def get_file_chunk_ids(self, filename):
        files = self._load()
        return files[filename]['chunks']

    def append_file_chunk_id(self, filename, chunk_id):
        files = self._load()
        files[filename]['chunks'].append(chunk_id)
        self._save(files)

    def clear_file_chunk_ids(self, filename):
        files = self._load()
        files[filename]['chunks'] = []
        self._save(files)
