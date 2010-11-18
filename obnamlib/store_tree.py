# Copyright 2010  Lars Wirzenius
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


import btree

import obnamlib


class StoreTree(object):

    '''A B-tree within a Store.'''

    def __init__(self, fs, dirname, key_bytes, node_size, upload_queue_size,
                 lru_size):
        self.fs = fs
        self.dirname = dirname
        self.key_bytes = key_bytes
        self.node_size = node_size
        self.upload_queue_size = upload_queue_size
        self.lru_size = lru_size
        self.forest = None

    def init_forest(self):
        if self.forest is None:
            if not self.fs.exists(self.dirname):
                return False
            codec = btree.NodeCodec(self.key_bytes)
            ns = obnamlib.NodeStoreVfs(self.fs, 
                              self.dirname, self.node_size, codec,
                              self.upload_queue_size, self.lru_size)
            self.forest = btree.Forest(ns)
        return True

    def require_forest(self):
        if not self.fs.exists(self.dirname):
            self.fs.mkdir(self.dirname)
        self.init_forest()
        assert self.forest is not None

    def commit(self):
        if self.forest:
            self.require_forest()
            self.forest.commit()

