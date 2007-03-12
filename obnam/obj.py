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


"""Backup objects"""

import logging

import uuid

from obnam.exception import ExceptionBase
import obnam.cmp
import obnam.varint


# Magic cookie at the beginning of every block

BLOCK_COOKIE = "blockhead\n"


# Version of the storage format

FORMAT_VERSION = "1"


# Constants of object kinds

_object_kinds = {}

def _define_kind(code, name):
    assert code not in _object_kinds
    assert name not in _object_kinds.values()
    _object_kinds[code] = name
    return code

FILEPART     = _define_kind(1, "FILEPART")
# object kind 2 used to be INODE, but it's been removed
GEN          = _define_kind(3, "GEN")
SIG          = _define_kind(4, "SIG")
HOST         = _define_kind(5, "HOST")
FILECONTENTS = _define_kind(6, "FILECONTENTS")
FILELIST     = _define_kind(7, "FILELIST")
DELTA        = _define_kind(8, "DELTA")
DELTAPART    = _define_kind(9, "DELTAPART")


def kind_name(kind):
    """Return a textual name for a numeric object kind"""
    return _object_kinds.get(kind, "UNKNOWN")


def object_id_new():
    """Return a string that is a universally unique ID for an object"""
    id = str(uuid.uuid4())
    logging.debug("Creating object id %s" % id)
    return id


class Object:

    def __init__(self, id, kind):
        self.id = id
        self.kind = kind
        self.components = []

    def add(self, c):
        """Add a component"""
        self.components.append(c)

    def get_kind(self):
        """Return the kind of an object"""
        return self.kind
    
        
def create(id, kind):
    """Create a new backup object"""
    return Object(id, kind)


def get_id(o):
    """Return the identifier for an object"""
    return o.id
    
    
def get_components(o):
    """Return list of all components in an object"""
    return o.components


def find_by_kind(o, wanted_kind):
    """Find all components of a desired kind inside this object"""
    return [c for c in get_components(o) if c.get_kind() == wanted_kind]


def find_strings_by_kind(o, wanted_kind):
    """Find all components of a desired kind, return their string values"""
    return [c.get_string_value() for c in find_by_kind(o, wanted_kind)]


def find_varints_by_kind(o, wanted_kind):
    """Find all components of a desired kind, return their varint values"""
    return [c.get_varint_value() for c in find_by_kind(o, wanted_kind)]


def first_by_kind(o, wanted_kind):
    """Find first component of a desired kind"""
    for c in get_components(o):
        if c.get_kind() == wanted_kind:
            return c
    return None


def first_string_by_kind(o, wanted_kind):
    """Find string value of first component of a desired kind"""
    c = first_by_kind(o, wanted_kind)
    if c:
        return c.get_string_value()
    else:
        return None


def first_varint_by_kind(o, wanted_kind):
    """Find string value of first component of a desired kind"""
    c = first_by_kind(o, wanted_kind)
    if c:
        return c.get_varint_value()
    else:
        return None


def encode(o):
    """Encode an object as a string"""
    id = obnam.cmp.Component(obnam.cmp.OBJID, o.id)
    kind = obnam.cmp.Component(obnam.cmp.OBJKIND, 
                                     obnam.varint.encode(o.kind))
    list = [id, kind] + get_components(o)
    list = [c.encode() for c in list]
    return "".join(list)


def decode(encoded, pos):
    """Decode an object from a string"""
    parser = obnam.cmp.Parser(encoded, pos)
    list = parser.decode_all()
    o = create("", 0)
    for c in list:
        if c.kind == obnam.cmp.OBJID:
            o.id = c.get_string_value()
        elif c.kind == obnam.cmp.OBJKIND:
            o.kind = c.get_string_value()
            (o.kind, _) = obnam.varint.decode(o.kind, 0)
        else:
            o.add(c)
    return o


class ObjectQueue:

    def __init__(self):
        self.clear()
        
    def add(self, object_id, encoded_object):
        self.queue.append((object_id, encoded_object))
        self.size += len(encoded_object)
        
    def clear(self):
        self.queue = []
        self.size = 0


def queue_create():
    """Create an empty object queue"""
    return ObjectQueue()


def queue_clear(oq):
    """Remove all objects from an object queue"""
    oq.clear()


def queue_add(oq, object_id, object):
    """Add an encoded object into an object queue"""
    oq.add(object_id, object)


def queue_is_empty(oq):
    """Is an object queue empty?"""
    return oq.size == 0


def queue_combined_size(oq):
    """Return the combined size of all objects in an object queue"""
    return oq.size


def queue_ids(oq):
    """Return identifiers for all the objects in the object queue"""
    return [x[0] for x in oq.queue]


def block_create_from_object_queue(blkid, oq):
    """Create a block from an object queue"""
    logging.debug("Creating block %s" % blkid)
    blkid = obnam.cmp.Component(obnam.cmp.BLKID, blkid)
    objects = [obnam.cmp.Component(obnam.cmp.OBJECT, x[1]) for x in oq.queue]
    return "".join([BLOCK_COOKIE] + 
                   [c.encode() for c in [blkid] + objects])


def block_decode(block):
    """Return list of decoded components in block, or None on error"""
    if block.startswith(BLOCK_COOKIE):
        parser = obnam.cmp.Parser(block, len(BLOCK_COOKIE))
        return parser.decode_all()
    else:
        logging.debug("xxx block does not start with cookie: %s" % repr(block))
        return None

    
def signature_object_encode(objid, sigdata):
    """Encode a SIG object"""
    c = obnam.cmp.Component(obnam.cmp.SIGDATA, sigdata)
    o = create(objid, SIG)
    o.add(c)
    return encode(o)


def delta_object_encode(objid, deltapart_refs, cont_ref, delta_ref):
    """Encode a DELTA object"""
    o = create(objid, DELTA)
    for deltapart_ref in deltapart_refs:
        o.add(obnam.cmp.Component(obnam.cmp.DELTAPARTREF, deltapart_ref))
    if cont_ref:
        c = obnam.cmp.Component(obnam.cmp.CONTREF, cont_ref)
    else:
        c = obnam.cmp.Component(obnam.cmp.DELTAREF, delta_ref)
    o.add(c)
    return encode(o)


def generation_object_encode(objid, filelist_id, start_time, end_time):
    """Encode a generation object, from list of filename, inode_id pairs"""
    o = create(objid, GEN)
    o.add(obnam.cmp.Component(obnam.cmp.FILELISTREF, filelist_id))
    o.add(obnam.cmp.Component(obnam.cmp.GENSTART, 
                              obnam.varint.encode(start_time)))
    o.add(obnam.cmp.Component(obnam.cmp.GENEND, 
                              obnam.varint.encode(end_time)))
    return encode(o)


def generation_object_decode(gen):
    """Decode a generation object into objid, file list ref"""

    o = decode(gen, 0)
    return o.id, first_string_by_kind(o, obnam.cmp.FILELISTREF), \
           first_varint_by_kind(o, obnam.cmp.GENSTART), \
           first_varint_by_kind(o, obnam.cmp.GENEND)


def host_block_encode(host_id, gen_ids, map_block_ids, contmap_block_ids):
    """Encode a new block with a host object"""
    o = create(host_id, HOST)
    
    c = obnam.cmp.Component(obnam.cmp.FORMATVERSION, FORMAT_VERSION)
    o.add(c)

    for gen_id in gen_ids:
        c = obnam.cmp.Component(obnam.cmp.GENREF, gen_id)
        o.add(c)
    
    for map_block_id in map_block_ids:
        c = obnam.cmp.Component(obnam.cmp.MAPREF, map_block_id)
        o.add(c)
    
    for map_block_id in contmap_block_ids:
        c = obnam.cmp.Component(obnam.cmp.CONTMAPREF, map_block_id)
        o.add(c)

    oq = queue_create()
    queue_add(oq, host_id, encode(o))
    block = block_create_from_object_queue(host_id, oq)
    return block


def host_block_decode(block):
    """Decode a host block"""
    
    list = block_decode(block)
    
    host_id = obnam.cmp.first_string_by_kind(list, obnam.cmp.BLKID)
    
    gen_ids = []
    map_ids = []
    contmap_ids = []

    objparts = obnam.cmp.find_by_kind(list, obnam.cmp.OBJECT)
    for objpart in objparts:
        subs = objpart.get_subcomponents()
        gen_ids += obnam.cmp.find_strings_by_kind(subs, obnam.cmp.GENREF)
        map_ids += obnam.cmp.find_strings_by_kind(subs, obnam.cmp.MAPREF)
        contmap_ids += obnam.cmp.find_strings_by_kind(subs, 
                                                      obnam.cmp.CONTMAPREF)

    return host_id, gen_ids, map_ids, contmap_ids
