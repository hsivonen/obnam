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


import larch

import obnamlib


class RepositoryTree(object):

    '''A B-tree within an obnamlib.Repository.
    
    For read-only operation, call init_forest before doing anything.
    
    For read-write operation, call start_changes before doing anything,
    and commit afterwards. In between, self.tree is the new tree to be 
    modified. Note that self.tree is NOT available after init_forest.
    
    After init_forest or start_changes, self.forest is the opened forest.
    Unlike self.tree, it will not go away after commit.
    
    '''

    def __init__(self, fs, dirname, key_bytes, node_size, upload_queue_size,
                 lru_size):
        self.fs = fs
        self.dirname = dirname
        self.key_bytes = key_bytes
        self.node_size = node_size
        self.upload_queue_size = upload_queue_size
        self.lru_size = lru_size
        self.forest = None
        self.tree = None
        self.keep_just_one_tree = False

    def init_forest(self):
        if self.forest is None:
            assert self.tree is None
            if not self.fs.exists(self.dirname):
                return False
            self.forest = larch.open_forest(key_size=self.key_bytes,
                                            node_size=self.node_size,
                                            dirname=self.dirname,
                                            upload_max=self.upload_queue_size,
                                            lru_size=self.lru_size,
                                            vfs=self.fs)
        return True

    def start_changes(self):
        if not self.fs.exists(self.dirname):
            self.fs.mkdir(self.dirname)
        self.init_forest()
        assert self.forest is not None
        if self.tree is None:
            if self.forest.trees:
                self.tree = self.forest.new_tree(self.forest.trees[-1])
            else:
                self.tree = self.forest.new_tree()

    def commit(self):
        if self.forest:
            if self.keep_just_one_tree:
                while len(self.forest.trees) > 1:
                    self.forest.remove_tree(self.forest.trees[0])
            self.forest.commit()
            self.tree = None

