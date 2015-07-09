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
        self._data = {}
        self._data_is_loaded = False

    def commit(self):
        self._load_data()
        self._finish_current_generation_if_any()
        self._save_data()

    def _finish_current_generation_if_any(self):
        generations = self._get_generations()
        if generations:
            keys = generations[-1]['keys']
            key_name = obnamlib.repo_key_name(obnamlib.REPO_GENERATION_ENDED)
            if keys[key_name] is None:
                keys[key_name] = int(self._current_time())

    def _get_generations(self):
        return self._data.get('generations', [])

    def _save_data(self):
        blob = obnamlib.serialise_object(self._data)
        filename = self._get_filename()
        self._fs.overwrite_file(filename, blob)

    def _get_filename(self):
        return os.path.join(self.get_dirname(), 'data.dat')

    def get_client_generation_ids(self):
        self._load_data()
        generations = self._get_generations()
        return [
            obnamlib.GenerationId(self._client_name, gen['id'])
            for gen in generations]

    def _load_data(self):
        if not self._data_is_loaded:
            filename = self._get_filename()
            if self._fs.exists(filename):
                blob = self._fs.cat(filename)
                self._data = obnamlib.deserialise_object(blob)
                assert self._data is not None
            else:
                self._data = {}
            self._data_is_loaded = True

    def create_generation(self):
        self._load_data()
        self._require_previous_generation_is_finished()

        generations = self._get_generations()
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
        generations = self._get_generations()
        if generations:
            keys = generations[-1]['keys']
            key_name = obnamlib.repo_key_name(obnamlib.REPO_GENERATION_ENDED)
            if keys[key_name] is None:
                raise obnamlib.RepositoryClientGenerationUnfinished(
                    client_name=self._client_name)

    def _new_generation_number(self):
        generations = self._get_generations()
        ids = [int(gen['id']) for gen in generations]
        if ids:
            newest_id = ids[-1]
            next_id = newest_id + 1
        else:
            next_id = 1
        return str(next_id)

    def remove_generation(self, gen_number):
        self._load_data()
        generations = self._get_generations()
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
        self._load_data()
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
        generations = self._get_generations()
        for generation in generations:
            if generation['id'] == gen_number:
                return generation
        raise obnamlib.RepositoryGenerationDoesNotExist(
            gen_id=gen_number, client_name=self._client_name)

    def set_generation_key(self, gen_number, key, value):
        self._load_data()
        generation = self._lookup_generation_by_gen_number(gen_number)
        generation['keys'][obnamlib.repo_key_name(key)] = value

    def file_exists(self, gen_number, filename):
        self._load_data()
        try:
            generation = self._lookup_generation_by_gen_number(gen_number)
        except obnamlib.RepositoryGenerationDoesNotExist:
            return False
        return filename in generation['files']

    def add_file(self, gen_number, filename):
        self._load_data()
        generation = self._lookup_generation_by_gen_number(gen_number)
        if filename not in generation['files']:
            generation['files'][filename] = {
                'keys': {},
                'chunks': [],
            }

    def remove_file(self, gen_number, filename):
        self._load_data()
        generation = self._lookup_generation_by_gen_number(gen_number)
        if filename in generation['files']:
            del generation['files'][filename]

    def get_file_key(self, gen_number, filename, key):
        self._load_data()
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
        self._load_data()
        self._require_file_exists(gen_number, filename)
        generation = self._lookup_generation_by_gen_number(gen_number)
        files = generation['files']
        key_name = obnamlib.repo_key_name(key)
        files[filename]['keys'][key_name] = value

    def get_file_chunk_ids(self, gen_number, filename):
        self._load_data()
        self._require_file_exists(gen_number, filename)
        generation = self._lookup_generation_by_gen_number(gen_number)
        return generation['files'][filename]['chunks']

    def append_file_chunk_id(self, gen_number, filename, chunk_id):
        self._load_data()
        self._require_file_exists(gen_number, filename)
        generation = self._lookup_generation_by_gen_number(gen_number)
        generation['files'][filename]['chunks'].append(chunk_id)

    def clear_file_chunk_ids(self, gen_number, filename):
        self._load_data()
        self._require_file_exists(gen_number, filename)
        generation = self._lookup_generation_by_gen_number(gen_number)
        generation['files'][filename]['chunks'] = []

    def get_generation_chunk_ids(self, gen_number):
        self._load_data()
        chunk_ids = set()
        generation = self._lookup_generation_by_gen_number(gen_number)
        for filename in generation['files']:
            file_chunk_ids = generation['files'][filename]['chunks']
            chunk_ids = chunk_ids.union(set(file_chunk_ids))
        return list(chunk_ids)

    def get_file_children(self, gen_number, filename):
        self._load_data()
        self._require_file_exists(gen_number, filename)
        generation = self._lookup_generation_by_gen_number(gen_number)
        return [
            x for x in generation['files']
            if self._is_direct_child_of(x, filename)]

    def _is_direct_child_of(self, child, parent):
        return os.path.dirname(child) == parent and child != parent
