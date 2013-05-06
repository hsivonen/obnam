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


class RepositoryFormatDummy(obnamlib.RepositoryInterface):

    '''Simplistic repository format for testing.

    This class exists to exercise the RepositoryInterfaceTests class.

    '''

    format = 'dummy'

    def __init__(self):
        self._client_names = []
        self._saved_client_names = None
        self._client_list_is_locked = False

    def set_fs(self, fs):
        pass

    def init_repo(self):
        pass

    def get_client_names(self):
        return self._client_names

    def lock_client_list(self):
        if self._client_list_is_locked:
            raise obnamlib.RepositoryClientListLockingFailed()
        self._client_list_is_locked = True
        self._saved_client_names = self._client_names[:]

    def unlock_client_list(self):
        if not self._client_list_is_locked:
            raise obnamlib.RepositoryClientListNotLocked()
        self._client_list_is_locked = False
        self._client_names = self._saved_client_names
        self._saved_client_names = None

    def commit_client_list(self):
        if not self._client_list_is_locked:
            raise obnamlib.RepositoryClientListNotLocked()
        self._client_list_is_locked = False
        self._saved_client_names = None

    def force_client_list_lock(self):
        if self._client_list_is_locked:
            self.unlock_client_list()
        self.lock_client_list()

    def _require_client_list_lock(self):
        if not self._client_list_is_locked:
            raise obnamlib.RepositoryClientListNotLocked()

    def add_client(self, client_name):
        self._require_client_list_lock()
        if client_name in self._client_names:
            raise obnamlib.RepositoryClientAlreadyExists(client_name)
        self._client_names.append(client_name)

    def remove_client(self, client_name):
        self._require_client_list_lock()
        if client_name not in self._client_names:
            raise obnamlib.RepositoryClientDoesNotExist(client_name)
        self._client_names.remove(client_name)

