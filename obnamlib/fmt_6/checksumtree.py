# Copyright 2010-2014  Lars Wirzenius
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


import struct
import tracing

import obnamlib


class ChecksumTree(obnamlib.RepositoryTree):

    '''Repository map of checksum to integer id.

    The checksum might be, for example, an MD5 one (as returned by
    hashlib.md5().digest()). The id would be a chunk id.

    '''

    def __init__(self, fs, name, checksum_length, node_size,
                 upload_queue_size, lru_size, hooks):
        tracing.trace('new ChecksumTree name=%s' % name)
        self.fmt = '!%dsQQ' % checksum_length
        key_bytes = struct.calcsize(self.fmt)
        obnamlib.RepositoryTree.__init__(self, fs, name, key_bytes, node_size,
                                         upload_queue_size, lru_size, hooks)
        self.keep_just_one_tree = True

    def key(self, checksum, chunk_id, client_id):
        return struct.pack(self.fmt, checksum, chunk_id, client_id)

    def unkey(self, key):
        return struct.unpack(self.fmt, key)

    def add(self, checksum, chunk_id, client_id):
        tracing.trace('checksum=%s', repr(checksum))
        tracing.trace('chunk_id=%s', chunk_id)
        tracing.trace('client_id=%s', client_id)
        self.start_changes()
        key = self.key(checksum, chunk_id, client_id)
        self.tree.insert(key, '')

    def find(self, checksum):
        if self.init_forest() and self.forest.trees:
            minkey = self.key(checksum, 0, 0)
            maxkey = self.key(checksum, obnamlib.MAX_ID, obnamlib.MAX_ID)
            t = self.forest.trees[-1]
            pairs = t.lookup_range(minkey, maxkey)
            return [self.unkey(key)[1] for key, value in pairs]
        else:
            return []

    def remove(self, checksum, chunk_id, client_id):
        tracing.trace('checksum=%s', repr(checksum))
        tracing.trace('chunk_id=%s', chunk_id)
        tracing.trace('client_id=%s', client_id)
        self.start_changes()
        key = self.key(checksum, chunk_id, client_id)
        self.tree.remove_range(key, key)

    def chunk_is_used(self, checksum, chunk_id):
        '''Is a given chunk used by anyone?'''
        if self.init_forest() and self.forest.trees:
            minkey = self.key(checksum, chunk_id, 0)
            maxkey = self.key(checksum, chunk_id, obnamlib.MAX_ID)
            t = self.forest.trees[-1]
            return not t.range_is_empty(minkey, maxkey)
        else:
            return False

