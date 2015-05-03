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
import hashlib
import errno
import os
import random
import StringIO

import tracing
import yaml

import obnamlib


class RepositoryDelegator(obnamlib.RepositoryInterface):

    '''Implement RepositoryInterface by delegating to other objects.'''

    def __init__(self, **kwargs):
        self._fs = None
        self._hooks = kwargs['hooks']
        self._lock_timeout = kwargs.get('lock_timeout', 0)

        self._client_finder = ClientFinder()
        self._client_finder.set_current_time(kwargs['current_time'])

    def set_client_list_object(self, client_list):
        self._client_list = client_list
        self._client_finder.set_client_list(self._client_list)

    def set_chunk_store_object(self, chunk_store):
        self._chunk_store = chunk_store

    def set_chunk_indexes_object(self, chunk_indexes):
        self._chunk_indexes = chunk_indexes

    def set_client_factory(self, client_factory):
        self._client_finder.set_client_factory(client_factory)

    def get_fs(self):
        return self._fs.fs

    def set_fs(self, fs):
        self._fs = obnamlib.RepositoryFS(self, fs, self._hooks)
        self._lockmgr = obnamlib.LockManager(self._fs, self._lock_timeout, '')

        self._client_list.set_fs(self._fs)
        self._client_list.set_lock_manager(self._lockmgr)
        self._client_list.set_hooks(self._hooks)

        self._client_finder.set_fs(self._fs)
        self._client_finder.set_lock_manager(self._lockmgr)

        self._chunk_store.set_fs(self._fs)

        self._chunk_indexes.set_fs(self._fs)
        self._chunk_indexes.set_lock_manager(self._lockmgr)


    #
    # Client list methods.
    #

    def get_client_names(self):
        return self._client_list.get_client_names()

    def lock_client_list(self):
        self._client_list.lock()

    def unlock_client_list(self):
        self._client_list.unlock()

    def commit_client_list(self):
        self._client_list.commit()

    def got_client_list_lock(self):
        return self._client_list.got_lock

    def force_client_list_lock(self):
        return self._client_list.force_lock()

    def add_client(self, client_name):
        self._client_list.add_client(client_name)

    def remove_client(self, client_name):
        self._client_list.remove_client(client_name)

    def rename_client(self, old_client_name, new_client_name):
        self._client_list.rename_client(old_client_name, new_client_name)

    def get_client_encryption_key_id(self, client_name):
        return self._client_list.get_client_encryption_key_id(client_name)

    def set_client_encryption_key_id(self, client_name, key_id):
        return self._client_list.set_client_encryption_key_id(
            client_name, key_id)

    #
    # Per-client methods.
    #

    def client_is_locked(self, client_name):
        return self._lookup_client(client_name).is_locked()

    def _lookup_client(self, client_name):
        return self._client_finder.find_client(client_name)

    def lock_client(self, client_name):
        self._lookup_client(client_name).lock()

    def unlock_client(self, client_name):
        self._lookup_client(client_name).unlock()

    def commit_client(self, client_name):
        self._lookup_client(client_name).commit()

    def got_client_lock(self, client_name):
        return self._lookup_client(client_name).got_lock

    def force_client_lock(self, client_name):
        self._lookup_client(client_name).force_lock()

    def get_client_generation_ids(self, client_name):
        return self._lookup_client(client_name).get_client_generation_ids()

    def create_generation(self, client_name):
        return self._lookup_client(client_name).create_generation()

    def get_generation_key(self, generation_id, key):
        client = self._lookup_client_by_generation(generation_id)
        return client.get_generation_key(generation_id.gen_number, key)

    def _lookup_client_by_generation(self, generation_id):
        return self._lookup_client(generation_id.client_name)

    def set_generation_key(self, generation_id, key, value):
        if key not in self.get_allowed_generation_keys():
            raise obnamlib.RepositoryGenerationKeyNotAllowed(
                client_name=generation_id.client_name,
                format=self.format,
                key_name=obnamlib.repo_key_name(key))
        client = self._lookup_client_by_generation(generation_id)
        return client.set_generation_key(generation_id.gen_number, key, value)

    def remove_generation(self, generation_id):
        client = self._lookup_client_by_generation(generation_id)
        return client.remove_generation(generation_id.gen_number)

    def get_generation_chunk_ids(self, generation_id):
        client = self._lookup_client_by_generation(generation_id)
        return client.get_generation_chunk_ids(generation_id.gen_number)

    def file_exists(self, generation_id, filename):
        client = self._lookup_client_by_generation(generation_id)
        return client.file_exists(generation_id.gen_number, filename)

    def add_file(self, generation_id, filename):
        client = self._lookup_client_by_generation(generation_id)
        return client.add_file(generation_id.gen_number, filename)

    def remove_file(self, generation_id, filename):
        client = self._lookup_client_by_generation(generation_id)
        return client.remove_file(generation_id.gen_number, filename)

    def get_file_key(self, generation_id, filename, key):
        if key not in self.get_allowed_file_keys():
            raise obnamlib.RepositoryFileKeyNotAllowed(
                client_name=generation_id.client_name,
                format=self.format)

        client = self._lookup_client_by_generation(generation_id)
        return client.get_file_key(generation_id.gen_number, filename, key)

    def set_file_key(self, generation_id, filename, key, value):
        if key not in self.get_allowed_file_keys():
            raise obnamlib.RepositoryFileKeyNotAllowed(
                client_name=generation_id.client_name,
                format=self.format)

        client = self._lookup_client_by_generation(generation_id)
        return client.set_file_key(
            generation_id.gen_number, filename, key, value)

    def get_file_chunk_ids(self, generation_id, filename):
        client = self._lookup_client_by_generation(generation_id)
        return client.get_file_chunk_ids(generation_id.gen_number, filename)

    def append_file_chunk_id(self, generation_id, filename, chunk_id):
        client = self._lookup_client_by_generation(generation_id)
        return client.append_file_chunk_id(
            generation_id.gen_number, filename, chunk_id)

    def clear_file_chunk_ids(self, generation_id, filename):
        client = self._lookup_client_by_generation(generation_id)
        return client.clear_file_chunk_ids(generation_id.gen_number, filename)

    def get_file_children(self, generation_id, filename):
        client = self._lookup_client_by_generation(generation_id)
        return client.get_file_children(generation_id.gen_number, filename)

    #
    # Chunk storage methods.
    #

    def put_chunk_content(self, content):
        return self._chunk_store.put_chunk_content(content)

    def get_chunk_content(self, chunk_id):
        return self._chunk_store.get_chunk_content(chunk_id)

    def has_chunk(self, chunk_id):
        return self._chunk_store.has_chunk(chunk_id)

    def remove_chunk(self, chunk_id):
        return self._chunk_store.remove_chunk(chunk_id)

    def get_chunk_ids(self):
        return self._chunk_store.get_chunk_ids()

    #
    # Chunk indexes methods.
    #

    def lock_chunk_indexes(self):
        self._chunk_indexes.lock()

    def unlock_chunk_indexes(self):
        self._chunk_indexes.unlock()

    def commit_chunk_indexes(self):
        self._chunk_indexes.commit()

    def got_chunk_indexes_lock(self):
        return self._chunk_indexes.got_lock

    def force_chunk_indexes_lock(self):
        self._chunk_indexes.force_lock()

    def prepare_chunk_for_indexes(self, chunk_content):
        return self._chunk_indexes.prepare_chunk_for_indexes(chunk_content)

    def put_chunk_into_indexes(self, chunk_id, token, client_id):
        return self._chunk_indexes.put_chunk_into_indexes(
            chunk_id, token, client_id)

    def find_chunk_ids_by_content(self, chunk_content):
        return self._chunk_indexes.find_chunk_ids_by_content(chunk_content)

    def remove_chunk_from_indexes(self, chunk_id, client_id):
        self._chunk_indexes.remove_chunk_from_indexes(chunk_id, client_id)

    def remove_chunk_from_indexes_for_all_clients(self, chunk_id):
        self._chunk_indexes.remove_chunk_from_indexes_for_all_clients(chunk_id)

    def validate_chunk_content(self, chunk_id):
        return self._chunk_indexes.validate_chunk_content(chunk_id)


class ClientFinder(object):

    def __init__(self):
        self._client_factory = None
        self._fs = None
        self._lockmgr = None
        self._client_list = None
        self._clients = {}
        self._current_time = None

    def set_client_factory(self, client_factory):
        self._client_factory = client_factory

    def set_fs(self, fs):
        self._fs = fs

    def set_lock_manager(self, lockmgr):
        self._lockmgr = lockmgr

    def set_client_list(self, client_list):
        self._client_list = client_list

    def set_current_time(self, current_time):
        self._current_time = current_time

    def find_client(self, client_name):
        if client_name not in self._client_list.get_client_names():
            raise obnamlib.RepositoryClientDoesNotExist(
                client_name=client_name)

        if client_name not in self._clients:
            client = self._client_factory(client_name)
            client.set_fs(self._fs)
            client.set_lock_manager(self._lockmgr)
            client.set_current_time(self._current_time)
            self._clients[client_name] = client

        return self._clients[client_name]
