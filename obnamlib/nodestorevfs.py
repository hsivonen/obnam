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


class NodeStoreVfs(btree.NodeStoreDisk):

    def __init__(self, fs, dirname, node_size, codec, upload_queue_size,
                 lru_size):
        btree.NodeStoreDisk.__init__(self, dirname, node_size, codec,
                                     upload_max=upload_queue_size,
                                     lru_size=lru_size)
        self.fs = fs
        
    def mkdir(self, dirname):
        if not self.fs.exists(dirname):
            self.fs.makedirs(dirname)

    def read_file(self, filename):
        return self.fs.cat(filename)

    def write_file(self, filename, contents):
        self.fs.overwrite_file(filename, contents, make_backup=False)

    def file_exists(self, filename):
        return self.fs.exists(filename)

    def rename_file(self, old, new):
        self.fs.rename(old, new)

    def remove_file(self, filename): # pragma: no cover
        self.fs.remove(filename)

    def listdir(self, dirname): # pragma: no cover
        return self.fs.listdir(dirname)

