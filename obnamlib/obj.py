# Copyright (C) 2006, 2007, 2008  Lars Wirzenius <liw@iki.fi>
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

import obnamlib


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

FILEPART     = _define_kind( 1, "FILEPART")
# object kind 2 used to be INODE, but it's been removed
GEN          = _define_kind( 3, "GEN")
SIG          = _define_kind( 4, "SIG")
HOST         = _define_kind( 5, "HOST")
FILECONTENTS = _define_kind( 6, "FILECONTENTS")
FILELIST     = _define_kind( 7, "FILELIST")
DELTA        = _define_kind( 8, "DELTA")
DELTAPART    = _define_kind( 9, "DELTAPART")
DIR          = _define_kind(10, "DIR")
FILEGROUP    = _define_kind(11, "FILEGROUP")


def kind_name(kind):
    """Return a textual name for a numeric object kind"""
    return _object_kinds.get(kind, "UNKNOWN")


def object_id_new():
    """Return a string that is a universally unique ID for an object"""
    id = str(uuid.uuid4())
    logging.debug("Creating object id %s" % id)
    return id


class StorageObject(object):

    """Implement a storage object in memory.
    
    There should be a sub-class of this class for every kind of storage
    object. Sub-class may implement a constructor, but their construct
    MUST accept a components= argument and pass it on to the base class
    constructor.
    
    Additionally, sub-classes MUST define the "kind" attribute to refer
    to the kind of storage object they are. This is required for
    the StorageObjectFactory to work.
    
    """
    
    kind = None

    def __init__(self, components=None, id=None):
        assert components is not None or id is not None
        if components:
            self._components = components
        else:
            self._components = []

        if id:
            self.set_id(id)
        if self.first_varint_by_kind(obnamlib.cmp.OBJKIND) is None and self.kind:
            self.add(obnamlib.cmp.Component(obnamlib.cmp.OBJKIND,
                                         obnamlib.varint.encode(self.kind)))

    def remove(self, kind):
        """Remove all components of a given kind."""
        self._components = [c for c in self.get_components()
                            if c.kind != kind]

    def add(self, c):
        """Add a component"""
        self._components.append(c)

    def replace(self, c):
        """Remove any existing components of this kind, then add this one."""
        self.remove(c.kind)
        self.add(c)

    def get_kind(self):
        """Return the kind of an object"""
        return self.first_varint_by_kind(obnamlib.cmp.OBJKIND)

    def get_id(self):
        """Return the identifier for an object"""
        return self.first_string_by_kind(obnamlib.cmp.OBJID)

    def set_id(self, id):
        """Set the identifier for this object."""
        self.replace(obnamlib.cmp.Component(obnamlib.cmp.OBJID, id))
            
    def get_components(self):
        """Return list of all components in an object"""
        return self._components
    
    def find_by_kind(self, wanted_kind):
        """Find all components of a desired kind inside this object"""
        return [c for c in self.get_components() 
                    if c.kind == wanted_kind]

    def find_strings_by_kind(self, wanted_kind):
        """Find all components of a desired kind, return string values"""
        return [c.str for c in self.find_by_kind(wanted_kind)]

    def find_varints_by_kind(self, wanted_kind):
        """Find all components of a desired kind, return varint values"""
        return [c.get_varint_value() for c in self.find_by_kind(wanted_kind)]

    def first_by_kind(self, wanted_kind):
        """Find first component of a desired kind"""
        for c in self.get_components():
            if c.kind == wanted_kind:
                return c
        return None

    def first_string_by_kind(self, wanted_kind):
        """Find string value of first component of a desired kind"""
        c = self.first_by_kind(wanted_kind)
        if c:
            return c.str
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
        return "".join(c.encode() for c in self.get_components())


# This function is only used during testing.
def decode(encoded):
    """Decode an object from a string"""
    parser = obnamlib.cmp.Parser(encoded)
    list = parser.decode_all()
    return StorageObject(components=list)


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
        blkid = obnamlib.cmp.Component(obnamlib.cmp.BLKID, blkid)
        objects = [obnamlib.cmp.Component(obnamlib.cmp.OBJECT, x[1]) 
                   for x in self.queue]
        return "".join([BLOCK_COOKIE] + 
                       [c.encode() for c in [blkid] + objects])


class BlockWithoutCookie(obnamlib.ObnamException):

    def __init__(self, block):
        self._msg = ("Block does not start with cookie: %s" %
                     " ".join("%02x" % ord(c) for c in block[:32]))


class EmptyBlock(obnamlib.ObnamException):

    def __init__(self):
        self._msg = "Block has no components."


def block_decode(block):
    """Return list of decoded components in block, or None on error"""
    if block.startswith(BLOCK_COOKIE):
        parser = obnamlib.cmp.Parser(block, len(BLOCK_COOKIE))
        list = parser.decode_all()
        if not list:
            raise EmptyBlock()
        return list
    else:
        raise BlockWithoutCookie(block)


class SignatureObject(StorageObject):

    kind = SIG

    def __init__(self, components=None, id=None, sigdata=None):
        StorageObject.__init__(self, components=components, id=id)
        if sigdata:
            c = obnamlib.cmp.Component(obnamlib.cmp.SIGDATA, sigdata)
            self.add(c)


class DeltaObject(StorageObject):

    kind = DELTA

    def __init__(self, components=None, id=None, deltapart_refs=None, 
                 cont_ref=None, delta_ref=None):
        StorageObject.__init__(self, components=components, id=id)
        if deltapart_refs:
            for deltapart_ref in deltapart_refs:
                c = obnamlib.cmp.Component(obnamlib.cmp.DELTAPARTREF, deltapart_ref)
                self.add(c)
        if cont_ref:
            c = obnamlib.cmp.Component(obnamlib.cmp.CONTREF, cont_ref)
            self.add(c)
        elif delta_ref:
            c = obnamlib.cmp.Component(obnamlib.cmp.DELTAREF, delta_ref)
            self.add(c)


class GenerationObject(StorageObject):

    kind = GEN

    def __init__(self, components=None, id=None, filelist_id=None, 
                 dirrefs=None, filegrouprefs=None, start=None, end=None,
                 is_snapshot=False):
        StorageObject.__init__(self, components=components, id=id)
        if filelist_id:
            self.add(obnamlib.cmp.Component(obnamlib.cmp.FILELISTREF, filelist_id))
        if dirrefs:
            for ref in dirrefs:
                self.add(obnamlib.cmp.Component(obnamlib.cmp.DIRREF, ref))
        if filegrouprefs:
            for ref in filegrouprefs:
                self.add(obnamlib.cmp.Component(obnamlib.cmp.FILEGROUPREF, ref))
        if start:
            self.add(obnamlib.cmp.Component(obnamlib.cmp.GENSTART, 
                                         obnamlib.varint.encode(start)))
        if end:
            self.add(obnamlib.cmp.Component(obnamlib.cmp.GENEND, 
                                         obnamlib.varint.encode(end)))
        if is_snapshot:
            self.add(obnamlib.cmp.Component(obnamlib.cmp.SNAPSHOTGEN,
                                            obnamlib.varint.encode(1)))

    def get_filelistref(self):
        return self.first_string_by_kind(obnamlib.cmp.FILELISTREF)

    def get_dirrefs(self):
        return self.find_strings_by_kind(obnamlib.cmp.DIRREF)

    def get_filegrouprefs(self):
        return self.find_strings_by_kind(obnamlib.cmp.FILEGROUPREF)

    def get_start_time(self):
        return self.first_varint_by_kind(obnamlib.cmp.GENSTART)

    def get_end_time(self):
        return self.first_varint_by_kind(obnamlib.cmp.GENEND)

    def is_snapshot(self):
        c = self.first_by_kind(obnamlib.cmp.SNAPSHOTGEN)
        return c and c.get_varint_value() == 1


# This is used only by testing.
def generation_object_decode(gen):
    """Decode a generation object into objid, file list ref"""

    o = decode(gen)
    return o.get_id(), \
           o.first_string_by_kind(obnamlib.cmp.FILELISTREF), \
           o.find_strings_by_kind(obnamlib.cmp.DIRREF), \
           o.find_strings_by_kind(obnamlib.cmp.FILEGROUPREF), \
           o.first_varint_by_kind(obnamlib.cmp.GENSTART), \
           o.first_varint_by_kind(obnamlib.cmp.GENEND)


class HostBlockObject(StorageObject):

    kind = HOST

    def __init__(self, components=None, host_id=None, gen_ids=None, 
                 map_block_ids=None, contmap_block_ids=None):
        StorageObject.__init__(self, components=components, id=host_id)
        
        if components is None:
            c = obnamlib.cmp.Component(obnamlib.cmp.FORMATVERSION, FORMAT_VERSION)
            self.add(c)
    
        if gen_ids:
            for gen_id in gen_ids:
                c = obnamlib.cmp.Component(obnamlib.cmp.GENREF, gen_id)
                self.add(c)
    
        if map_block_ids:
            for map_block_id in map_block_ids:
                c = obnamlib.cmp.Component(obnamlib.cmp.MAPREF, map_block_id)
                self.add(c)
        
        if contmap_block_ids:
            for map_block_id in contmap_block_ids:
                c = obnamlib.cmp.Component(obnamlib.cmp.CONTMAPREF, map_block_id)
                self.add(c)
    
    def get_generation_ids(self):
        """Return IDs of all generations for this host."""
        return self.find_strings_by_kind(obnamlib.cmp.GENREF)
    
    def get_map_block_ids(self):
        """Return IDs of all map blocks for this host."""
        return self.find_strings_by_kind(obnamlib.cmp.MAPREF)
    
    def get_contmap_block_ids(self):
        """Return IDs of all map blocks for this host."""
        return self.find_strings_by_kind(obnamlib.cmp.CONTMAPREF)
    
    def encode(self):
        oq = ObjectQueue()
        oq.add(self.get_id(), StorageObject.encode(self))
        return oq.as_block(self.get_id())


def create_host_from_block(block):
    """Decode a host block into a HostBlockObject"""
    
    list = block_decode(block)
    
    host_id = obnamlib.cmp.first_string_by_kind(list, obnamlib.cmp.BLKID)
    
    gen_ids = []
    map_ids = []
    contmap_ids = []

    objparts = obnamlib.cmp.find_by_kind(list, obnamlib.cmp.OBJECT)
    for objpart in objparts:
        gen_ids += objpart.find_strings_by_kind(obnamlib.cmp.GENREF)
        map_ids += objpart.find_strings_by_kind(obnamlib.cmp.MAPREF)
        contmap_ids += objpart.find_strings_by_kind(obnamlib.cmp.CONTMAPREF)

    return HostBlockObject(host_id=host_id, gen_ids=gen_ids,
                           map_block_ids=map_ids, 
                           contmap_block_ids=contmap_ids)


class DirObject(StorageObject):

    kind = DIR

    def __init__(self, components=None, id=None, name=None, stat=None, 
                 dirrefs=None, filegrouprefs=None):
        StorageObject.__init__(self, components=components, id=id)
        if name:
            self.add(obnamlib.cmp.Component(obnamlib.cmp.FILENAME, name))
        self.name = name
        if stat:
            self.add(obnamlib.cmp.create_stat_component(stat))
        if dirrefs:
            for ref in dirrefs:
                self.add(obnamlib.cmp.Component(obnamlib.cmp.DIRREF, ref))
        if filegrouprefs:
            for ref in filegrouprefs:
                self.add(obnamlib.cmp.Component(obnamlib.cmp.FILEGROUPREF, ref))

    def get_name(self):
        if not self.name:
            self.name = self.first_by_kind(obnamlib.cmp.FILENAME).str
        return self.name

    def get_stat(self):
        st = self.first_by_kind(obnamlib.cmp.STAT)
        return obnamlib.cmp.parse_stat_component(st)

    def get_dirrefs(self):
        return [c.str for c in self.find_by_kind(obnamlib.cmp.DIRREF)]

    def get_filegrouprefs(self):
        return [c.str for c in self.find_by_kind(obnamlib.cmp.FILEGROUPREF)]


class FileGroupObject(StorageObject):

    kind = FILEGROUP

    def __init__(self, components=None, id=None):
        StorageObject.__init__(self, components=components, id=id)
        self.populate_caches()

    def populate_caches(self):
        self.cache_file = {}
        self.cache_stat = {}
        for c in self.get_files(): # pragma: no cover
            self.add_to_caches(c)
    
    def add_to_caches(self, file_component):
        name = file_component.first_string_by_kind(obnamlib.cmp.FILENAME)
        self.cache_file[name] = file_component

        c = file_component.first_by_kind(obnamlib.cmp.STAT)
        self.cache_stat[file_component] = obnamlib.cmp.parse_stat_component(c)
    
    def add_file(self, name, stat, contref, sigref, deltaref):
        c = obnamlib.filelist.create_file_component_from_stat(name, stat, 
                                                           contref, sigref, 
                                                           deltaref)
        self.add(c)
        self.add_to_caches(c)

    def get_files(self):
        return self.find_by_kind(obnamlib.cmp.FILE)

    def get_file(self, name):
        return self.cache_file.get(name, None)

    def get_string_from_file(self, file, kind):
        return file.first_string_by_kind(kind)

    def get_stat_from_file(self, file):
        return self.cache_stat.get(file, None)

    def get_names(self):
        return [self.get_string_from_file(x, obnamlib.cmp.FILENAME) 
                for x in self.get_files()]

    def get_stat(self, filename):
        return self.get_stat_from_file(self.get_file(filename))

    def get_contref(self, filename):
        return self.get_string_from_file(self.get_file(filename),
                                         obnamlib.cmp.CONTREF)

    def get_sigref(self, filename):
        return self.get_string_from_file(self.get_file(filename),
                                         obnamlib.cmp.SIGREF)

    def get_deltaref(self, filename):
        return self.get_string_from_file(self.get_file(filename),
                                         obnamlib.cmp.DELTAREF)


class FileListObject(StorageObject):

    kind = FILELIST


class FilePartObject(StorageObject):

    kind = FILEPART


class FileContentsObject(StorageObject):

    kind = FILECONTENTS


class DeltaPartObject(StorageObject):

    kind = DELTAPART


class UnknownStorageObjectKind(obnamlib.ObnamException):

    def __init__(self, kind):
        self._msg = "Unknown storage object kind %s" % kind


class StorageObjectFactory:

    """Create the right kind of Object subclass instance.
    
    Given a parsed component representing an object, figure out the type
    of the object and instantiate the right sub-class of Object.
    
    """
    
    def __init__(self):
        self._classes = []
        for n, klass in globals().iteritems():
            if (type(klass) is type(StorageObject) and 
                klass != StorageObject and
                issubclass(klass, StorageObject)):
                self._classes.append(klass)
    
    def get_object(self, components):
        kind = obnamlib.cmp.first_varint_by_kind(components, obnamlib.cmp.OBJKIND)
        for klass in self._classes:
            if klass.kind == kind:
                return klass(components=components)
        raise UnknownStorageObjectKind(kind)
