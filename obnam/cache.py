# Copyright (C) 2006  Lars Wirzenius <liw@iki.fi>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.


"""Block cache for backup program"""


import os


class Cache:

    def __init__(self, config):
        self.cachedir = config.get("backup", "cache")

    def cache_pathname(self, block_id):
        """Return pathname in local block cache for a given block id"""
        return os.path.join(self.cachedir, block_id)
    
    
    def create_new_cache_file(self, block_id):
        """Create a new file in the local block cache, open for writing"""
        pathname = self.cache_pathname(block_id)
        dirname = os.path.dirname(pathname)
        if not os.path.isdir(dirname):
            os.makedirs(dirname, 0700)
        return file(pathname + ".new", "w", 0600)
    
    def close_new_cache_file(self, block_id, f):
        """Close a file opened by open_cache_file"""
        f.close()
        pathname = self.cache_pathname(block_id)
        os.rename(pathname + ".new", pathname)
    
    def put_block(self, block_id, block):
        """Put a block into the cache"""
        f = self.create_new_cache_file(block_id)
        f.write(block)
        self.close_new_cache_file(block_id, f)
    
    def get_block(self, block_id):
        """Return the contents of a block in the block cache, or None"""
        try:
            f = file(self.cache_pathname(block_id), "r")
            block = f.read()
            f.close()
        except IOError, e:
            return None
        return block
