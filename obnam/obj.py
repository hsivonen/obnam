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

    def get_id(self):
        """Return the identifier for an object"""
        return self.id
            
    def get_components(self):
        """Return list of all components in an object"""
        return self.components
    
    def find_by_kind(self, wanted_kind):
        """Find all components of a desired kind inside this object"""
        return [c for c in self.get_components() 
                    if c.get_kind() == wanted_kind]

    def find_strings_by_kind(self, wanted_kind):
        """Find all components of a desired kind, return string values"""
        return [c.get_string_value() for c in self.find_by_kind(wanted_kind)]

    def find_varints_by_kind(self, wanted_kind):
        """Find all components of a desired kind, return varint values"""
        return [c.get_varint_value() for c in self.find_by_kind(wanted_kind)]

    def first_by_kind(self, wanted_kind):
        """Find first component of a desired kind"""
        for c in self.get_components():
            if c.get_kind() == wanted_kind:
                return c
        return None

    def first_string_by_kind(self, wanted_kind):
        """Find string value of first component of a desired kind"""
        c = self.first_by_kind(wanted_kind)
        if c:
            return c.get_string_value()
        else:
            return None

    def first_varint_by_kind(self, wanted_kind):
        """Find string value of first component of a desired kind"""
        c = self.first_by_kind(wanted_kind)
        if c:
            return c.get_varint_value()
        else:
            return None

    def encode(self):
        """Encode an object as a string"""
        id = obnam.cmp.Component(obnam.cmp.OBJID, self.id)
        kind = obnam.cmp.Component(obnam.cmp.OBJKIND, 
                                   obnam.varint.encode(self.kind))
        list = [id, kind] + self.get_components()
        list = [c.encode() for c in list]
        return "".join(list)


# This function is only used during testing.
def decode(encoded):
    """Decode an object from a string"""
    parser = obnam.cmp.Parser(encoded)
    list = parser.decode_all()
    o = Object("", 0)
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
        """Add an encoded object into an object queue"""
        self.queue.append((object_id, encoded_object))
        self.size += len(encoded_object)
        
    def clear(self):
        """Remove all objects from an object queue"""
        self.queue = []
        self.size = 0

    def is_empty(self):
        """Is an object queue empty?"""
        return self.size == 0

    def combined_size(self):
        """Return the combined size of all objects in an object queue"""
        return self.size

    def ids(self):
        """Return identifiers for all the objects in the object queue"""
        return [x[0] for x in self.queue]

    def as_block(self, blkid):
        """Create a block from an object queue"""
        logging.debug("Creating block %s" % blkid)
        blkid = obnam.cmp.Component(obnam.cmp.BLKID, blkid)
        objects = [obnam.cmp.Component(obnam.cmp.OBJECT, x[1]) 
                   for x in self.queue]
        return "".join([BLOCK_COOKIE] + 
                       [c.encode() for c in [blkid] + objects])


def block_decode(block):
    """Return list of decoded components in block, or None on error"""
    if block.startswith(BLOCK_COOKIE):
        parser = obnam.cmp.Parser(block, len(BLOCK_COOKIE))
        return parser.decode_all()
    else:
        logging.warning("Block does not start with cookie: %s" % repr(block))
        return None


class SignatureObject(Object):

    def __init__(self, objid, sigdata):
        Object.__init__(self, objid, SIG)
        c = obnam.cmp.Component(obnam.cmp.SIGDATA, sigdata)
        self.add(c)


class DeltaObject(Object):

    def __init__(self, objid, deltapart_refs, cont_ref, delta_ref):
        Object.__init__(self, objid, DELTA)
        for deltapart_ref in deltapart_refs:
            c = obnam.cmp.Component(obnam.cmp.DELTAPARTREF, deltapart_ref)
            self.add(c)
        if cont_ref:
            c = obnam.cmp.Component(obnam.cmp.CONTREF, cont_ref)
        else:
            c = obnam.cmp.Component(obnam.cmp.DELTAREF, delta_ref)
        self.add(c)


class GenerationObject(Object):

    def __init__(self, objid, filelist_id, start_time, end_time):
        Object.__init__(self, objid, GEN)
        self.add(obnam.cmp.Component(obnam.cmp.FILELISTREF, filelist_id))
        self.add(obnam.cmp.Component(obnam.cmp.GENSTART, 
                                     obnam.varint.encode(start_time)))
        self.add(obnam.cmp.Component(obnam.cmp.GENEND, 
                                     obnam.varint.encode(end_time)))


# This is used only by testing.
def generation_object_decode(gen):
    """Decode a generation object into objid, file list ref"""

    o = decode(gen)
    return o.id, o.first_string_by_kind(obnam.cmp.FILELISTREF), \
           o.first_varint_by_kind(obnam.cmp.GENSTART), \
           o.first_varint_by_kind(obnam.cmp.GENEND)


class HostBlockObject(Object):

    def __init__(self, host_id, gen_ids, map_block_ids, contmap_block_ids):
        Object.__init__(self, host_id, HOST)
        
        c = obnam.cmp.Component(obnam.cmp.FORMATVERSION, FORMAT_VERSION)
        self.add(c)
    
        for gen_id in gen_ids:
            c = obnam.cmp.Component(obnam.cmp.GENREF, gen_id)
            self.add(c)
        
        for map_block_id in map_block_ids:
            c = obnam.cmp.Component(obnam.cmp.MAPREF, map_block_id)
            self.add(c)
        
        for map_block_id in contmap_block_ids:
            c = obnam.cmp.Component(obnam.cmp.CONTMAPREF, map_block_id)
            self.add(c)
    
    def encode(self):
        oq = ObjectQueue()
        oq.add(self.id, Object.encode(self))
        return oq.as_block(self.id)


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
