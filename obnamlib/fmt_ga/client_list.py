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


import errno
import os
import random

import obnamlib


class GAClientList(object):

    def __init__(self):
        self._hooks = None
        self._fs = None
        self.set_dirname('client-list')
        self.clear()

    def set_hooks(self, hooks):
        self._hooks = hooks

    def set_fs(self, fs):
        self._fs = fs

    def set_dirname(self, dirname):
        self._dirname = dirname

    def get_dirname(self):
        return self._dirname

    def clear(self):
        self._data = None
        self._data_is_loaded = False
        self._added_clients = []

    def commit(self):
        self._load_data()
        for client_name in self._added_clients:
            self._hooks.call('repository-add-client', self, client_name)
        self._save_data()
        self._added_clients = []

    def _save_data(self):
        assert self._data is not None
        blob = obnamlib.serialise_object(self._data)
        filename = self._get_filename()
        self._fs.overwrite_file(filename, blob)

    def _get_filename(self):
        return os.path.join(self.get_dirname(), 'data.dat')

    def get_client_names(self):
        self._load_data()
        return self._data.get('clients', {}).keys()

    def _load_data(self):
        if self._data_is_loaded:
            assert self._data is not None
        else:
            assert self._data is None
        if not self._data_is_loaded:
            filename = self._get_filename()
            if self._fs.exists(filename):
                blob = self._fs.cat(filename)
                self._data = obnamlib.deserialise_object(blob)
                assert self._data is not None
            else:
                self._data = {
                    'clients': {},
                }
            self._data_is_loaded = True

    def get_client_dirname(self, client_name):
        self._load_data()
        return self._get_dirname_for_client_id(
            self._data['clients'][client_name]['client-id'])

    def _get_dirname_for_client_id(self, client_id):
        return 'clientdir-%s' % client_id

    def add_client(self, client_name):
        self._load_data()
        self._require_client_does_not_exist(client_name)

        clients = self._data.get('clients', {})
        clients[client_name] = {
            'encryption-key': None,
            'client-id': self._pick_client_id(),
        }
        self._data['clients'] = clients

        self._added_clients.append(client_name)

    def _pick_client_id(self):
        while True:
            candidate_id = random.randint(0, obnamlib.MAX_ID)
            dirname = self._get_dirname_for_client_id(candidate_id)
            try:
                self._fs.create_and_init_toplevel(dirname)
            except OSError as e:
                if e.errno == e.EEXIST:
                    continue
                raise
            return candidate_id

    def remove_client(self, client_name):
        self._load_data()
        self._require_client_exists(client_name)

        clients = self._data.get('clients', {})
        del clients[client_name]
        self._data['clients'] = clients

        if client_name in self._added_clients:
            self._added_clients.remove(client_name)

    def rename_client(self, old_client_name, new_client_name):
        self._load_data()
        self._require_client_exists(old_client_name)
        self._require_client_does_not_exist(new_client_name)

        clients = self._data.get('clients', {})
        clients[new_client_name] = clients[old_client_name]
        del clients[old_client_name]
        self._data['clients'] = clients

        if old_client_name in self._added_clients:  # pragma: no cover
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
        self._load_data()
        self._require_client_exists(client_name)
        return self._data['clients'][client_name]['encryption-key']

    def set_client_encryption_key_id(self, client_name, encryption_key):
        self._load_data()
        self._require_client_exists(client_name)
        self._data['clients'][client_name]['encryption-key'] = encryption_key
