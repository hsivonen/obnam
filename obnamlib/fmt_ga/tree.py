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


import os

import obnamlib


class GATree(object):

    def __init__(self):
        self._blob_store = None
        self._dir_objs = {}
        self._root_dir_id = None

    def set_blob_store(self, blob_store):
        self._blob_store = blob_store

    def set_root_directory_id(self, root_dir_id):
        self._root_dir_id = root_dir_id

    def get_root_directory_id(self):
        return self._root_dir_id

    def get_directory(self, pathname):
        if pathname in self._dir_objs:
            return self._dir_objs[pathname]

        if self._root_dir_id is None:
            return None

        if pathname == '/':
            return self._get_dir_obj(self._root_dir_id)

        parent_path = os.path.dirname(pathname)
        parent_obj = self.get_directory(parent_path)
        if parent_obj is None:  # pragma: no cover
            return None
        obj_id = parent_obj.get_subdir_object_id(os.path.basename(pathname))
        if obj_id is None:  # pragma: no cover
            return None
        return self._get_dir_obj(obj_id)

    def _get_dir_obj(self, dir_id):
        blob = self._blob_store.get_blob(dir_id)
        if blob is None:  # pragma: no cover
            return None
        as_dict = obnamlib.deserialise_object(blob)
        dir_obj = obnamlib.create_gadirectory_from_dict(as_dict)
        dir_obj.set_immutable()
        return dir_obj

    def set_directory(self, pathname, dir_obj):
        self._dir_objs[pathname] = dir_obj
        if pathname != '/':
            parent_path = os.path.dirname(pathname)
            parent_obj = self.get_directory(parent_path)
            if not parent_obj:
                parent_obj = self._create_fake_parent(
                    os.path.basename(pathname), dir_obj)
                self.set_directory(parent_path, parent_obj)

    def _create_fake_parent(self, subdir_basename, subdir_obj):
        parent_obj = obnamlib.GADirectory()
        parent_obj.add_subdir(subdir_basename, None)
        return parent_obj

    def flush(self):
        self._root_dir_id = self._fixup_subdir_refs('/')
        self._blob_store.flush()
        self._dir_objs = {}

    def _fixup_subdir_refs(self, pathname):
        dir_obj = self._dir_objs[pathname]
        for basename in dir_obj.get_subdir_basenames():
            if dir_obj.get_subdir_object_id(basename) is None:
                assert dir_obj.is_mutable()
                subdir_path = os.path.join(pathname, basename)
                subdir_id = self._fixup_subdir_refs(subdir_path)
                dir_obj.add_subdir(basename, subdir_id)
        return self._put_dir_obj(dir_obj)

    def _put_dir_obj(self, dir_obj):
        dir_obj.set_immutable()
        blob = obnamlib.serialise_object(dir_obj.as_dict())
        return self._blob_store.put_blob(blob)
