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
        self._client_keys = GAClientKeys()
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
        data = {
            'keys': self._client_keys.as_dict(),
            'generations': [g.as_dict() for g in self._generations],
        }
        blob = obnamlib.serialise_object(data)
        filename = self._get_filename()
        self._fs.overwrite_file(filename, blob)

    def _get_filename(self):
        return os.path.join(self.get_dirname(), 'data.dat')

    def get_client_generation_ids(self):
        self._load_data()
        return [
            obnamlib.GenerationId(self._client_name, gen.get_number())
            for gen in self._generations]

    def _load_data(self):
        if not self._data_is_loaded:
            self.clear()
            filename = self._get_filename()
            if self._fs.exists(filename):
                blob = self._fs.cat(filename)
                data = obnamlib.deserialise_object(blob)
                self._client_keys.set_from_dict(data['keys'])
                for gen_dict in data['generations']:
                    gen = GAGeneration()
                    gen.set_from_dict(gen_dict)
                    self._generations.append(gen)
            self._data_is_loaded = True

    def create_generation(self):
        self._load_data()
        self._require_previous_generation_is_finished()

        new_generation = GAGeneration()
        if self._generations:
            old_dict = self._generations.get_latest().as_dict()
            new_dict = copy.deepcopy(old_dict)
            new_generation.set_from_dict(new_dict)

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
            return ids[-1] + 1
        else:
            return 1

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
        return filename in generation.get_files_dict()

    def add_file(self, gen_number, filename):
        self._load_data()
        generation = self._lookup_generation_by_gen_number(gen_number)
        files_dict = generation.get_files_dict()
        if filename not in files_dict:
            files_dict[filename] = {
                'keys': {},
                'chunks': [],
            }

    def remove_file(self, gen_number, filename):
        self._load_data()
        generation = self._lookup_generation_by_gen_number(gen_number)
        files_dict = generation.get_files_dict()
        if filename in files_dict:
            del files_dict[filename]

    def get_file_key(self, gen_number, filename, key):
        self._load_data()
        self._require_file_exists(gen_number, filename)
        generation = self._lookup_generation_by_gen_number(gen_number)
        files = generation.get_files_dict()
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
        if filename not in generation.get_files_dict():
            raise obnamlib.RepositoryFileDoesNotExistInGeneration(
                client_name=self._client_name,
                genspec=gen_number,
                filename=filename)

    def set_file_key(self, gen_number, filename, key, value):
        self._load_data()
        self._require_file_exists(gen_number, filename)
        generation = self._lookup_generation_by_gen_number(gen_number)
        files = generation.get_files_dict()
        key_name = obnamlib.repo_key_name(key)
        files[filename]['keys'][key_name] = value

    def get_file_chunk_ids(self, gen_number, filename):
        self._load_data()
        self._require_file_exists(gen_number, filename)
        generation = self._lookup_generation_by_gen_number(gen_number)
        files = generation.get_files_dict()
        return files[filename]['chunks']

    def append_file_chunk_id(self, gen_number, filename, chunk_id):
        self._load_data()
        self._require_file_exists(gen_number, filename)
        generation = self._lookup_generation_by_gen_number(gen_number)
        files = generation.get_files_dict()
        files[filename]['chunks'].append(chunk_id)

    def clear_file_chunk_ids(self, gen_number, filename):
        self._load_data()
        self._require_file_exists(gen_number, filename)
        generation = self._lookup_generation_by_gen_number(gen_number)
        files = generation.get_files_dict()
        files[filename]['chunks'] = []

    def get_generation_chunk_ids(self, gen_number):
        self._load_data()
        chunk_ids = set()
        generation = self._lookup_generation_by_gen_number(gen_number)
        files = generation.get_files_dict()
        for filename in files:
            file_chunk_ids = files[filename]['chunks']
            chunk_ids = chunk_ids.union(set(file_chunk_ids))
        return list(chunk_ids)

    def get_file_children(self, gen_number, filename):
        self._load_data()
        self._require_file_exists(gen_number, filename)
        generation = self._lookup_generation_by_gen_number(gen_number)
        files = generation.get_files_dict()
        return [
            x for x in files
            if self._is_direct_child_of(x, filename)]

    def _is_direct_child_of(self, child, parent):
        return os.path.dirname(child) == parent and child != parent


class GAClientKeys(object):

    def __init__(self):
        self._dict = {}

    def as_dict(self):
        return self._dict

    def set_from_dict(self, keys_dict):
        self._dict = keys_dict

    def get_key(self, key):
        return self._dict.get(key)

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
        self._data = {
            'keys': {},
            'files': {},
        }

    def as_dict(self):
        return self._data

    def set_from_dict(self, data):
        self._data = data

    def get_number(self):
        return self._data['id']

    def set_number(self, new_id):
        self._data['id'] = new_id

    def keys(self):
        return self._data['keys'].keys()

    def get_key(self, key, default=None):
        return self._data['keys'].get(key, default)

    def set_key(self, key, value):
        self._data['keys'][key] = value

    def get_files_dict(self):
        return self._data['files']
