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


class RepositoryFormatSimple(obnamlib.RepositoryInterface):

    '''Simplistic repository format as an example.

    This class is an example of how to implement a repository format.

    '''

    format = 'simple'

    def __init__(self, **kwargs):
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
        raise NotImplementedError()

    def lock_client_list(self):
        raise NotImplementedError()

    def unlock_client_list(self):
        raise NotImplementedError()

    def commit_client_list(self):
        raise NotImplementedError()

    def got_client_list_lock(self):
        raise NotImplementedError()

    def force_client_list_lock(self):
        raise NotImplementedError()

    def add_client(self, client_name):
        raise NotImplementedError()

    def remove_client(self, client_name):
        raise NotImplementedError()

    def rename_client(self, old_client_name, new_client_name):
        raise NotImplementedError()

    def get_client_encryption_key_id(self, client_name):
        raise NotImplementedError()

    def set_client_encryption_key_id(self, client_name, key_id):
        raise NotImplementedError()

    def client_is_locked(self, client_name):
        raise NotImplementedError()

    def lock_client(self, client_name):
        raise NotImplementedError()

    def unlock_client(self, client_name):
        raise NotImplementedError()

    def commit_client(self, client_name):
        raise NotImplementedError()

    def got_client_lock(self, client_name):
        raise NotImplementedError()

    def force_client_lock(self, client_name):
        raise NotImplementedError()

    def get_allowed_client_keys(self):
        raise NotImplementedError()

    def get_client_key(self, client_name, key):
        raise NotImplementedError()

    def set_client_key(self, client_name, key, value):
        raise NotImplementedError()

    def get_client_generation_ids(self, client_name):
        raise NotImplementedError()

    def get_client_extra_data_directory(self, client_name):
        raise NotImplementedError()

    def create_generation(self, client_name):
        raise NotImplementedError()

    def get_allowed_generation_keys(self):
        raise NotImplementedError()

    def get_generation_key(self, generation_id, key):
        raise NotImplementedError()

    def set_generation_key(self, generation_id, key, value):
        raise NotImplementedError()

    def remove_generation(self, generation_id):
        raise NotImplementedError()

    def get_generation_chunk_ids(self, generation_id):
        raise NotImplementedError()

    def interpret_generation_spec(self, client_name, genspec):
        raise NotImplementedError()

    def make_generation_spec(self, generation_id):
        raise NotImplementedError()

    def file_exists(self, generation_id, filename):
        raise NotImplementedError()

    def add_file(self, generation_id, filename):
        raise NotImplementedError()

    def remove_file(self, generation_id, filename):
        raise NotImplementedError()

    def get_file_key(self, generation_id, filename, key):
        raise NotImplementedError()

    def set_file_key(self, generation_id, filename, key, value):
        raise NotImplementedError()

    def get_allowed_file_keys(self):
        raise NotImplementedError()

    def get_file_chunk_ids(self, generation_id, filename):
        raise NotImplementedError()

    def append_file_chunk_id(self, generation_id, filename, chunk_id):
        raise NotImplementedError()

    def clear_file_chunk_ids(self, generation_id, filename):
        raise NotImplementedError()

    def get_file_children(self, generation_id, filename):
        raise NotImplementedError()

    def put_chunk_content(self, content):
        raise NotImplementedError()

    def get_chunk_content(self, chunk_id):
        raise NotImplementedError()

    def has_chunk(self, chunk_id):
        raise NotImplementedError()

    def remove_chunk(self, chunk_id):
        raise NotImplementedError()

    def get_chunk_ids(self):
        raise NotImplementedError()

    def lock_chunk_indexes(self):
        raise NotImplementedError()

    def unlock_chunk_indexes(self):
        raise NotImplementedError()

    def commit_chunk_indexes(self):
        raise NotImplementedError()

    def got_chunk_indexes_lock(self):
        raise NotImplementedError()

    def force_chunk_indexes_lock(self):
        raise NotImplementedError()

    def prepare_chunk_for_indexes(self, chunk_content):
        raise NotImplementedError()

    def put_chunk_into_indexes(self, chunk_id, token, client_id):
        raise NotImplementedError()

    def find_chunk_ids_by_content(self, chunk_content):
        raise NotImplementedError()

    def remove_chunk_from_indexes(self, chunk_id, client_id):
        raise NotImplementedError()

    def remove_chunk_from_indexes_for_all_clients(self, chunk_id):
        raise NotImplementedError()

    def validate_chunk_content(self, chunk_id):
        raise NotImplementedError()

    def get_fsck_work_items(self):
        raise NotImplementedError()
