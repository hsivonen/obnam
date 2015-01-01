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


import os

import yaml

import obnamlib


class SimpleLock(object):

    def __init__(self):
        self._lockmgr = None
        self._dirname = None
        self.got_lock = False

    def set_lock_manager(self, lockmgr):
        self._lockmgr = lockmgr

    def set_dirname(self, dirname):
        self._dirname = dirname

    def unchecked_lock(self):
        self._lockmgr.lock([self._dirname])
        self.got_lock = True

    def unchecked_unlock(self):
        self._lockmgr.unlock([self._dirname])
        self.got_lock = False

    def force(self):
        if self._lockmgr.is_locked(self._dirname):
            self.unchecked_unlock()


class SimpleData(object):

    def __init__(self):
        self._fs = None
        self._data_name = None
        self._obj = {}

    def set_fs(self, fs):
        self._fs = fs

    def set_data_pathname(self, data_name):
        self._data_name = data_name

    def load(self):
        if self._obj is not None and self._fs.exists(self._data_name):
            f = self._fs.open(self._data_name, 'rb')
            self._obj = yaml.safe_load(f)
            f.close()

    def save(self):
        f = self._fs.open(self._data_name, 'wb')
        yaml.safe_dump(self._obj, stream=f)
        f.close()

    def clear(self):
        self._obj = {}

    def __getitem__(self, key):
        self.load()
        return self._obj[key]

    def __setitem__(self, key, value):
        self.load()
        self._obj[key] = value

    def get(self, key, default=None):
        self.load()
        return self._obj.get(key, default)


class SimpleToplevel(object):

    def __init__(self):
        self._lock = SimpleLock()
        self._data = SimpleData()

    def set_fs(self, fs):
        self._data.set_fs(fs)

    def set_dirname(self, dirname):
        self._lock.set_dirname(dirname)
        self._data.set_data_pathname(os.path.join(dirname, 'data.yaml'))

    def set_lock_manager(self, lockmgr):
        self._lock.set_lock_manager(lockmgr)


class SimpleClientList(SimpleToplevel):

    # We store the client list in JSON as follows:
    #
    #   {
    #       "clients": {
    #           "foo": {}
    #       }
    #   }
    #
    # Above, the client name is foo.

    def __init__(self):
        SimpleToplevel.__init__(self)
        self.set_dirname('client-list')

    @property
    def got_lock(self):
        return self._lock.got_lock

    def lock(self):
        if self._lock.got_lock:
            raise obnamlib.RepositoryClientListLockingFailed()
        self._lock.unchecked_lock()
        self._data.clear()

    def unlock(self):
        if not self._lock.got_lock:
            raise obnamlib.RepositoryClientListNotLocked()
        self._data.clear()
        self._lock.unchecked_unlock()

    def commit(self):
        if not self._lock.got_lock:
            raise obnamlib.RepositoryClientListNotLocked()
        self._data.save()
        self._lock.unchecked_unlock()

    def force_lock(self):
        self._lock.force()
        self._data.clear()

    def get_client_names(self):
        return self._data.get('clients', {}).keys()

    def add_client(self, client_name):
        if not self._lock.got_lock:
            raise obnamlib.RepositoryClientListNotLocked()

        self._require_client_does_not_exist(client_name)

        clients = self._data.get('clients', {})
        clients[client_name] = {}
        self._data['clients'] = clients
        
    def remove_client(self, client_name):
        if not self._lock.got_lock:
            raise obnamlib.RepositoryClientListNotLocked()

        self._require_client_exists(client_name)

        clients = self._data.get('clients', {})
        del clients[client_name]
        self._data['clients'] = clients

    def rename_client(self, old_client_name, new_client_name):
        if not self._lock.got_lock:
            raise obnamlib.RepositoryClientListNotLocked()

        self._require_client_exists(old_client_name)
        self._require_client_does_not_exist(new_client_name)

        clients = self._data.get('clients', {})
        clients[new_client_name] = clients[old_client_name]
        del clients[old_client_name]
        self._data['clients'] = clients

    def _require_client_exists(self, client_name):
        if client_name not in self._data.get('clients', {}):
            raise obnamlib.RepositoryClientDoesNotExist(
                client_name=client_name)

    def _require_client_does_not_exist(self, client_name):
        if client_name in self._data.get('clients', {}):
            raise obnamlib.RepositoryClientAlreadyExists(
                client_name=client_name)


class RepositoryFormatSimple(obnamlib.RepositoryInterface):

    '''Simplistic repository format as an example.

    This class is an example of how to implement a repository format.

    '''

    format = 'simple'

    def __init__(self, **kwargs):
        self._fs = None
        self._lock_timeout = kwargs.get('lock_timeout', 0)
        self._client_list = SimpleClientList()

    def get_fs(self):
        return self._fs

    def set_fs(self, fs):
        self._fs = fs
        self._lockmgr = obnamlib.LockManager(self._fs, self._lock_timeout, '')

        self._client_list.set_fs(self._fs)
        self._client_list.set_lock_manager(self._lockmgr)

    def init_repo(self):
        pass

    def close(self):
        pass

    def get_fsck_work_items(self):
        raise NotImplementedError()

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
        raise NotImplementedError()

    def set_client_encryption_key_id(self, client_name, key_id):
        raise NotImplementedError()

    #
    # Per-client methods.
    #

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

    #
    # Chunk storage methods.
    #

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

    #
    # Chunk indexes methods.
    #

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
