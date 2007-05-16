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


def decode_block(mapping, mapping_block):
    """Decode a block with mappings, add them to mapping object"""
    logging.debug("Decoding mapping block")
    list = obnam.obj.block_decode(mapping_block)
    if not list:
        logging.debug("Mapping block is empty")
        return
    maps = obnam.cmp.find_by_kind(list, obnam.cmp.OBJMAP)
    logging.debug("Mapping block contains %d maps" % len(maps))
    for map in maps:
        subs = map.get_subcomponents()
        block_id = obnam.cmp.first_string_by_kind(subs, 
                                               obnam.cmp.BLOCKREF)
        object_ids = obnam.cmp.find_strings_by_kind(subs, 
                                               obnam.cmp.OBJREF)
        logging.debug("Map contains %d objects" % len(object_ids))
        if object_ids and block_id:
            for object_id in object_ids:
                logging.debug("Object %s in block %s" % (object_id, block_id))
                _add_old(mapping, object_id, block_id)
