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


import hashlib
import os

import obnamlib


class GAChunkIndexes(object):

    def __init__(self):
        self._fs = None
        self.set_dirname('chunk-indexes')
        self.clear()

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
        self._save_data()

    def _save_data(self):
        blob = obnamlib.serialise_object(self._data)
        filename = self._get_filename()
        self._fs.overwrite_file(filename, blob)

    def _get_filename(self):
        return os.path.join(self.get_dirname(), 'data.bag')

    def prepare_chunk_for_indexes(self, chunk_content):
        return hashlib.sha512(chunk_content).hexdigest()

    def put_chunk_into_indexes(self, chunk_id, token, client_id):
        self._load_data()
        self._prepare_data()
        self._data['index'].append({
            'chunk-id': chunk_id,
            'sha512': token,
            'client-id': client_id,
        })

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

    def _prepare_data(self):
        if 'index' not in self._data:
            self._data['index'] = []

    def find_chunk_ids_by_content(self, chunk_content):
        self._load_data()
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
        self._load_data()
        self._prepare_data()

        self._data['index'] = self._filter_out(
            self._data['index'],
            lambda x:
            x['chunk-id'] == chunk_id and x['client-id'] == client_id)

    def _filter_out(self, records, pred):
        return [record for record in records if not pred(record)]

    def remove_chunk_from_indexes_for_all_clients(self, chunk_id):
        self._load_data()
        self._prepare_data()

        self._data['index'] = self._filter_out(
            self._data['index'],
            lambda x: x['chunk-id'] == chunk_id)

    def validate_chunk_content(self, chunk_id):
        return None
