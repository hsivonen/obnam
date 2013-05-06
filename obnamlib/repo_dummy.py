# Copyright 2013  Lars Wirzenius
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

    def copy(self):
        other = KeyValueStore()
        for key in self._map:
            other.set_value(key, self._map[key])
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


class Counter(object):

    def __init__(self):
        self._latest = 0

    def next(self):
        self._latest += 1
        return self._latest


class DummyClient(object):

    def __init__(self, name):
        self.name = name
        self.new_name = None
        self.locked = False
        self.generation_counter = Counter()
        self.data = LockableKeyValueStore()

    def lock(self):
        if self.locked:
            raise obnamlib.RepositoryClientLockingFailed(self.name)
        self.locked = True
        self.data.lock()

    def _require_lock(self):
        if not self.locked:
            raise obnamlib.RepositoryClientNotLocked(self.name)

    def unlock(self):
        self._require_lock()
        self.data.unlock()
        self.locked = False

    def commit(self):
        self._require_lock()
        self.data.commit()
        self.locked = False

    def get_key(self, key):
        return self.data.get_value(key, '')

    def set_key(self, key, value):
        self._require_lock()
        self.data.set_value(key, value)

    def get_generation_ids(self):
        key = ('generation-ids',)
        return self.data.get_value(key, [])

    def create_generation(self):
        self._require_lock()
        generation_id = (self.name, self.generation_counter.next())
        key = ('generation-ids',)
        ids = self.data.get_value(key, [])
        ids.append(generation_id)
        self.data.set_value(key, ids)
        return generation_id


class DummyClientList(object):

    def __init__(self):
        self.locked = False
        self.clients = []
        self.wip_clients = None

    def lock(self):
        if self.locked:
            raise obnamlib.RepositoryClientListLockingFailed()
        self.locked = True
        self.wip_clients = self.clients[:]

    def unlock(self):
        if not self.locked:
            raise obnamlib.RepositoryClientListNotLocked()
        for client in self.wip_clients:
            client.new_name = None
        self.wip_clients = None
        self.locked = False

    def commit(self):
        if not self.locked:
            raise obnamlib.RepositoryClientListNotLocked()
        for client in self.wip_clients:
            if client.new_name is not None:
                client.name = client.new_name
        self.clients = self.wip_clients
        self.wip_clients = None
        self.locked = False

    def force(self):
        if self.locked:
            self.unlock()
        self.lock()

    def _require_lock(self):
        if not self.locked:
            raise obnamlib.RepositoryClientListNotLocked()

    def names(self):
        if self.locked:
            return [c.new_name or c.name for c in self.wip_clients]
        else:
            return [c.name for c in self.clients]

    def __getitem__(self, client_name):
        for client in self.clients:
            if client_name == client.name:
                return client
        raise obnamlib.RepositoryClientDoesNotExist(client_name)

    def add(self, client_name):
        self._require_lock()
        for client in self.wip_clients:
            if client.name == client_name:
                raise obnamlib.RepositoryClientAlreadyExists(client_name)
        self.wip_clients.append(DummyClient(client_name))

    def remove(self, client_name):
        self._require_lock()
        for client in self.wip_clients:
            if client_name in (client.name, client.new_name):
                self.wip_clients.remove(client)
                return
        raise obnamlib.RepositoryClientDoesNotExist(client_name)

    def rename(self, old_client_name, new_client_name):
        self._require_lock()
        names = [client.name for client in self.wip_clients]
        names.extend(c.new_name for c in self.wip_clients if c.new_name)
        if old_client_name not in names:
            raise obnamlib.RepositoryClientDoesNotExist(old_client_name)
        if new_client_name in names:
            raise obnamlib.RepositoryClientAlreadyExists(old_client_name)

        for client in self.wip_clients:
            if old_client_name in (client.name, client.new_name):
                client.new_name = new_client_name
                break


class RepositoryFormatDummy(obnamlib.RepositoryInterface):

    '''Simplistic repository format for testing.

    This class exists to exercise the RepositoryInterfaceTests class.

    '''

    format = 'dummy'

    def __init__(self):
        self._client_list = DummyClientList()

    def set_fs(self, fs):
        pass

    def init_repo(self):
        pass

    def get_client_names(self):
        return self._client_list.names()

    def lock_client_list(self):
        self._client_list.lock()

    def unlock_client_list(self):
        self._client_list.unlock()

    def commit_client_list(self):
        self._client_list.commit()

    def force_client_list_lock(self):
        self._client_list.force()

    def add_client(self, client_name):
        self._client_list.add(client_name)

    def remove_client(self, client_name):
        self._client_list.remove(client_name)

    def rename_client(self, old_client_name, new_client_name):
        self._client_list.rename(old_client_name, new_client_name)

    def lock_client(self, client_name):
        self._client_list[client_name].lock()

    def unlock_client(self, client_name):
        self._client_list[client_name].unlock()

    def commit_client(self, client_name):
        self._client_list[client_name].commit()

    def get_allowed_client_keys(self):
        return [obnamlib.REPO_CLIENT_TEST_KEY]

    def get_client_key(self, client_name, key):
        return self._client_list[client_name].get_key(key)

    def set_client_key(self, client_name, key, value):
        if key not in self.get_allowed_client_keys():
            raise obnamlib.RepositoryClientKeyNotAllowed(
                self.format, client_name, key)
        self._client_list[client_name].set_key(key, value)

    def get_client_generation_ids(self, client_name):
        return self._client_list[client_name].get_generation_ids()

    def create_generation(self, client_name):
        return self._client_list[client_name].create_generation()
