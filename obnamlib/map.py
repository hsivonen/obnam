# Copyright (C) 2006, 2008  Lars Wirzenius <liw@iki.fi>
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


"""Mapping of object to block identifiers"""


import random

import obnamlib


class KeyAlreadyInMapping(obnamlib.ObnamException):

    def __init__(self, object_id):
        self._msg = "Object ID %s already in mapping" % object_id


class Map:

    """A mapping from StorageObject identifiers to block identifiers.
    
    Both identifiers are unique strings.
    
    This class has a subset of the interface of a dictionary:
    "map[objid]" works for getting and setting values, and
    "objid in map" works as well.
    
    Additionally, this class keeps track of which mappings have been
    added.
    
    """

    def __init__(self, context):
        self.context = context
        self.dict = {}
        self.loaded_blocks = set()
        self.loadable_blocks = []
        self.max = 0
        self.reset_new()
        self.hits = 0
        self.misses = 0
        self.forgotten = 0

    def __getitem__(self, object_id):
        if object_id in self.dict:
            self.hits += 1
            return self.dict[object_id]
        self.misses += 1
        for map_block_id in self.loadable_blocks:
            if map_block_id not in self.loaded_blocks:
                block = self.fetch_block(self.context, map_block_id)
                self.loaded_blocks.add(map_block_id)
                self.decode_block(block)
                if object_id in self.dict:
                    return self.dict[object_id]
        return None

    def __setitem__(self, object_id, block_id):
        if object_id in self.dict:
            raise KeyAlreadyInMapping(object_id)
        self.dict[object_id] = block_id
        self.new_keys.add(object_id)
        if self.max > 0 and len(self.dict) > self.max:
            keys = self.dict.keys()
            for new_key in self.new_keys:
                keys.remove(new_key)
            while len(self.dict) > self.max and keys:
                self.forgotten += 1
                begone = random.choice(keys)
                del self.dict[begone]
                keys.remove(begone)
            # If we forget anything, we need to re-set the loaded blocks so
            # that we can get the mapping again.
            self.loaded_blocks.clear()

    def __contains__(self, object_id):
        return object_id in self.dict

    def __len__(self):
        return len(self.dict)

    def get_new(self):
        return self.new_keys

    def reset_new(self):
        self.new_keys = set()

    def encode_new(self):
        """Return a list of encoded components for the new mappings."""

        list = []
        dict = {}
        for object_id in self.get_new():
            block_id = self[object_id]
            if block_id in dict:
                dict[block_id].append(object_id)
            else:
                dict[block_id] = [object_id]
        for block_id in dict:
            object_ids = dict[block_id]
            object_ids = [obnamlib.cmp.Component(obnamlib.cmp.OBJREF, x)
                          for x in object_ids]
            block_id = obnamlib.cmp.Component(obnamlib.cmp.BLOCKREF, block_id)
            c = obnamlib.cmp.Component(obnamlib.cmp.OBJMAP, 
                                    [block_id] + object_ids)
            list.append(c.encode())
        return list

    def encode_new_to_block(self, block_id):
        """Encode new mappings into a block"""
        c = obnamlib.cmp.Component(obnamlib.cmp.BLKID, block_id)
        list = self.encode_new()
        block = "".join([obnamlib.obj.BLOCK_COOKIE, c.encode()] + list)
        return block

    def decode_block(self, block):
        """Decode a block with mappings, add them to the mapping."""

        # This function used to use the block and component parsing code
        # in obnamlib.obj and obnamlib.cmp, namely the
        # obnamlib.obj.block_decode function. However, it turned out to
        # be pretty slow, and since we load maps at the beginning of
        # pretty much any backup run, the following version was written,
        # and measured with benchmarks to run in about a quarter of the
        # speed of the original. If the structure of blocks changes,
        # this code needs to change as well.

        if not block.startswith(obnamlib.obj.BLOCK_COOKIE):
            raise obnamlib.obj.BlockWithoutCookie(block)
    
        pos = len(obnamlib.obj.BLOCK_COOKIE)
        end = len(block)

        original_new = self.new_keys
        self.new_keys = set()
        
        while pos < end:
            size, pos = obnamlib.varint.decode(block, pos)
            kind, pos = obnamlib.varint.decode(block, pos)
    
            if kind == obnamlib.cmp.OBJMAP:
                pos2 = pos
                end2 = pos + size
                block_id = None
                object_ids = []
                while pos2 < end2:
                    size2, pos2 = obnamlib.varint.decode(block, pos2)
                    kind2, pos2 = obnamlib.varint.decode(block, pos2)
                    data2 = block[pos2:pos2+size2]
                    pos2 += size2
                    if kind2 == obnamlib.cmp.BLOCKREF:
                        block_id = data2
                    elif kind2 == obnamlib.cmp.OBJREF:
                        object_ids.append(data2)
                if object_ids and block_id:
                    for object_id in object_ids:
                        self[object_id] = block_id
    
            pos += size

        self.new_keys = original_new
        
    def load_from_blocks(self, block_ids):
        """Add to the blocks from which to attempt demand loading.
        
        If __getitem__ can't find the block_id for a given object_id,
        it will attempt to load more mappings from the list of blocks
        given in `block_ids`. If that still fails, it will return None.
        The blocks are tried in the order given in `block_ids`.
        
        """
        self.loadable_blocks += block_ids

    def fetch_block(self, context, block_id):
        """Load a given block id, return it's contents.
        
        This is just a wrapper for obnamlib.io.get_block. It's purpose
        is to make it easy for unit tests to override this method with
        a mock version.
        
        """
        
        return obnamlib.io.get_block(context, block_id) # pragma: no cover
