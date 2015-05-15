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
import random

import obnamlib


class GAChunkStore(object):

    def __init__(self):
        self._fs = None
        self._dirname = 'chunk-store'

    def set_fs(self, fs):
        self._fs = fs

    def put_chunk_content(self, content):
        self._fs.create_and_init_toplevel(self._dirname)
        while True:
            chunk_id = self._random_chunk_id()
            filename = self._chunk_filename(chunk_id)
            try:
                self._fs.write_file(filename, content)
            except OSError, e: # pragma: no cover
                if e.errno == errno.EEXIST:
                    continue
                raise
            else:
                return chunk_id

    def get_chunk_content(self, chunk_id):
        filename = self._chunk_filename(chunk_id)
        if not self._fs.exists(filename):
            raise obnamlib.RepositoryChunkDoesNotExist(
                chunk_id=chunk_id,
                filename=filename)
        return self._fs.cat(filename)

    def has_chunk(self, chunk_id):
        filename = self._chunk_filename(chunk_id)
        return self._fs.exists(filename)

    def remove_chunk(self, chunk_id):
        filename = self._chunk_filename(chunk_id)
        if not self._fs.exists(filename):
            raise obnamlib.RepositoryChunkDoesNotExist(
                chunk_id=chunk_id,
                filename=filename)
        self._fs.remove(filename)

    def get_chunk_ids(self):
        if not self._fs.exists(self._dirname):
            return []
        basenames = self._fs.listdir(self._dirname)
        return [
            self._parse_chunk_filename(x)
            for x in basenames
            if x.endswith('.chunk')]

    def _random_chunk_id(self):
        return random.randint(0, obnamlib.MAX_ID)

    def _chunk_filename(self, chunk_id):
        return os.path.join(self._dirname, '%d.chunk' % chunk_id)

    def _parse_chunk_filename(self, filename):
        return int(filename[:-len('.chunk')])
