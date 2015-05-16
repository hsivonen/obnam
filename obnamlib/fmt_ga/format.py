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


class RepositoryFormatGA(obnamlib.RepositoryDelegator):

    format = 'green-albatross'

    def __init__(self, **kwargs):
        obnamlib.RepositoryDelegator.__init__(self, **kwargs)
        self.set_client_list_object(obnamlib.GAClientList())
        self.set_chunk_store_object(obnamlib.GAChunkStore())
        self.set_chunk_indexes_object(obnamlib.GAChunkIndexes())
        self.set_client_factory(obnamlib.GAClient)

    def init_repo(self):
        pass

    def close(self):
        pass

    def get_fsck_work_items(self):
        return []

    def get_shared_directories(self):
        return ['client-list', 'chunk-store', 'chunk-indexes']

    #
    # Per-client methods.
    #

    def get_allowed_client_keys(self):
        return []

    def get_client_key(self, client_name, key): # pragma: no cover
        raise obnamlib.RepositoryClientKeyNotAllowed(
            format=self.format,
            client_name=client_name,
            key_name=obnamlib.repo_key_name(key))

    def set_client_key(self, client_name, key, value):
        raise obnamlib.RepositoryClientKeyNotAllowed(
            format=self.format,
            client_name=client_name,
            key_name=obnamlib.repo_key_name(key))

    def get_client_extra_data_directory(self, client_name): # pragma: no cover
        if client_name not in self.get_client_names():
            raise obnamlib.RepositoryClientDoesNotExist(
                client_name=client_name)
        return self._client_list.get_client_dirname(client_name)

    def get_allowed_generation_keys(self):
        return [
            obnamlib.REPO_GENERATION_TEST_KEY,
            obnamlib.REPO_GENERATION_STARTED,
            obnamlib.REPO_GENERATION_ENDED,
            obnamlib.REPO_GENERATION_IS_CHECKPOINT,
            obnamlib.REPO_GENERATION_FILE_COUNT,
            obnamlib.REPO_GENERATION_TOTAL_DATA,
            ]

    def get_allowed_file_keys(self):
        return [obnamlib.REPO_FILE_TEST_KEY,
                obnamlib.REPO_FILE_MODE,
                obnamlib.REPO_FILE_MTIME_SEC,
                obnamlib.REPO_FILE_MTIME_NSEC,
                obnamlib.REPO_FILE_ATIME_SEC,
                obnamlib.REPO_FILE_ATIME_NSEC,
                obnamlib.REPO_FILE_NLINK,
                obnamlib.REPO_FILE_SIZE,
                obnamlib.REPO_FILE_UID,
                obnamlib.REPO_FILE_USERNAME,
                obnamlib.REPO_FILE_GID,
                obnamlib.REPO_FILE_GROUPNAME,
                obnamlib.REPO_FILE_SYMLINK_TARGET,
                obnamlib.REPO_FILE_XATTR_BLOB,
                obnamlib.REPO_FILE_BLOCKS,
                obnamlib.REPO_FILE_DEV,
                obnamlib.REPO_FILE_INO,
                obnamlib.REPO_FILE_MD5]

    def interpret_generation_spec(self, client_name, genspec):
        ids = self.get_client_generation_ids(client_name)
        if not ids:
            raise obnamlib.RepositoryClientHasNoGenerations(
                client_name=client_name)

        if genspec == 'latest':
            return ids[-1]

        for gen_id in ids:
            if self.make_generation_spec(gen_id) == genspec:
                return gen_id

        raise obnamlib.RepositoryGenerationDoesNotExist(
            client_name=client_name, gen_id=genspec)

    def make_generation_spec(self, generation_id):
        return generation_id.gen_number
