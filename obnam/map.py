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


"""Mapping of object to block identifiers"""

import logging

import obnam.cmp


class Mappings:

    def __init__(self):
        self.dict = {}
        self.new_keys = {}


def create():
    """Create a new object ID to block ID mapping"""
    return Mappings()


def count(mapping):
    """Return the number of mappings in 'mapping'"""
    return len(mapping.dict.keys())


def add(mapping, object_id, block_id):
    """Add a mapping from object_id to block_id"""
    _add_old(mapping, object_id, block_id)
    if object_id not in mapping.new_keys:
        mapping.new_keys[object_id] = 1


def _add_old(mapping, object_id, block_id):
    """Add a mapping from object_id to block_id"""
    assert object_id not in mapping.dict
    mapping.dict[object_id] = block_id


def get(mapping, object_id):
    """Return the list of blocks, in order, that contain parts of an object"""
    return mapping.dict.get(object_id, None)


def get_new(mapping):
    """Return list of new mappings"""
    return mapping.new_keys.keys()


def reset_new(mapping):
    """Reset list of new mappings"""
    mapping.new_keys = {}


def encode_new(mapping):
    """Return a list of encoded components for the new mappings"""
    list = []
    dict = {}
    for object_id in get_new(mapping):
        block_id = get(mapping, object_id)
        if block_id in dict:
            dict[block_id].append(object_id)
        else:
            dict[block_id] = [object_id]
    for block_id in dict:
        object_ids = dict[block_id]
        object_ids = [obnam.cmp.Component(obnam.cmp.OBJREF, x)
                      for x in object_ids]
        block_id = obnam.cmp.Component(obnam.cmp.BLOCKREF, block_id)
        c = obnam.cmp.Component(obnam.cmp.OBJMAP, 
                                [block_id] + object_ids)
        list.append(c.encode())
    return list


def encode_new_to_block(mapping, block_id):
    """Encode new mappings into a block"""
    c = obnam.cmp.Component(obnam.cmp.BLKID, block_id)
    list = encode_new(mapping)
    block = "".join([obnam.obj.BLOCK_COOKIE, c.encode()] + list)
    return block


# This function used to use the block and component parsing code in
# obnam.obj and obnam.cmp, namely the obnam.obj.block_decode function.
# However, it turned out to be pretty slow, and since we load maps at
# the beginning of pretty much any backup run, the following version was
# written, and measured with benchmarks to run in about a quarter of the
# speed of the original. If the structure of blocks changes, this code
# needs to change as well.

def decode_block(mapping, block):
    """Decode a block with mappings, add them to mapping object"""
    logging.debug("Decoding mapping block")
    
    if not block.startswith(obnam.obj.BLOCK_COOKIE):
        raise obnam.obj.BlockWithoutCookie(block)

    pos = len(obnam.obj.BLOCK_COOKIE)
    end = len(block)
    
    while pos < end:
        size, pos = obnam.varint.decode(block, pos)
        kind, pos = obnam.varint.decode(block, pos)

        if kind == obnam.cmp.OBJMAP:
            pos2 = pos
            end2 = pos + size
            block_id = None
            object_ids = []
            while pos2 < end2:
                size2, pos2 = obnam.varint.decode(block, pos2)
                kind2, pos2 = obnam.varint.decode(block, pos2)
                data2 = block[pos2:pos2+size2]
                pos2 += size2
                if kind2 == obnam.cmp.BLOCKREF:
                    block_id = data2
                elif kind2 == obnam.cmp.OBJREF:
                    object_ids.append(data2)
            if object_ids and block_id:
                for object_id in object_ids:
                    _add_old(mapping, object_id, block_id)

        pos += size
