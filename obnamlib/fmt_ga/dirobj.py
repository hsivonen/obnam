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


import obnamlib


class GADirectory(object):

    def __init__(self):
        self._dict = {
            'metadata': {},
            'subdirs': {},
        }
        self._mutable = True

    def is_mutable(self):
        return self._mutable

    def set_immutable(self):
        self._mutable = False

    def as_dict(self):
        return self._dict

    def add_file(self, basename):
        self._require_mutable()
        self._dict['metadata'][basename] = {
            'chunk-ids': [],
        }

    def _require_mutable(self):
        if not self._mutable:
            raise GAImmutableError()

    def remove_file(self, basename):
        self._require_mutable()
        if basename in self._dict['metadata']:
            del self._dict['metadata'][basename]

    def get_file_basenames(self):
        return self._dict['metadata'].keys()

    def get_file_key(self, basename, key):
        return self._dict['metadata'][basename].get(key)

    def set_file_key(self, basename, key, value):
        self._require_mutable()
        self._dict['metadata'][basename][key] = value

    def get_file_chunk_ids(self, basename):
        return self._dict['metadata'][basename]['chunk-ids']

    def append_file_chunk_id(self, basename, chunk_id):
        self._require_mutable()
        self._dict['metadata'][basename]['chunk-ids'].append(chunk_id)

    def clear_file_chunk_ids(self, basename):
        self._require_mutable()
        self._dict['metadata'][basename]['chunk-ids'] = []

    def get_subdir_basenames(self):
        return self._dict['subdirs'].keys()

    def add_subdir(self, basename, obj_id):
        self._require_mutable()
        self._dict['subdirs'][basename] = obj_id

    def remove_subdir(self, basename):
        self._require_mutable()
        if basename in self._dict['subdirs']:
            del self._dict['subdirs'][basename]

    def get_subdir_object_id(self, basename):
        return self._dict['subdirs'].get(basename)


class GAImmutableError(obnamlib.ObnamError):

    msg = 'Attempt to modify an immutable GADirectory'


def create_gadirectory_from_dict(a_dict):
    dir_obj = GADirectory()
    for basename in a_dict['metadata']:
        dir_obj.add_file(basename)
        for key, value in a_dict['metadata'][basename].items():
            dir_obj.set_file_key(basename, key, value)
    for subdir, obj_id in a_dict['subdirs'].items():
        dir_obj.add_subdir(subdir, obj_id)
    return dir_obj
