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
        if self.first_varint_by_kind(obnam.cmp.OBJKIND) is None and self.kind:
            self.add(obnam.cmp.Component(obnam.cmp.OBJKIND,
                                         obnam.varint.encode(self.kind)))

    def remove(self, kind):
        """Remove all components of a given kind."""
        self._components = [c for c in self.get_components()
                            if c.get_kind() != kind]

    def add(self, c):
        """Add a component"""
        self._components.append(c)

    def replace(self, c):
        """Remove any existing components of this kind, then add this one."""
        self.remove(c.get_kind())
        self.add(c)

    def get_kind(self):
        """Return the kind of an object"""
        return self.first_varint_by_kind(obnam.cmp.OBJKIND)

    def get_id(self):
        """Return the identifier for an object"""
        return self.first_string_by_kind(obnam.cmp.OBJID)

    def set_id(self, id):
        """Set the identifier for this object."""
        self.replace(obnam.cmp.Component(obnam.cmp.OBJID, id))
            
    def get_components(self):
        """Return list of all components in an object"""
        return self._components
    
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
        return "".join(c.encode() for c in self.get_components())


# This function is only used during testing.
def decode(encoded):
    """Decode an object from a string"""
    parser = obnam.cmp.Parser(encoded)
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
        blkid = obnam.cmp.Component(obnam.cmp.BLKID, blkid)
        objects = [obnam.cmp.Component(obnam.cmp.OBJECT, x[1]) 
                   for x in self.queue]
        return "".join([BLOCK_COOKIE] + 
                       [c.encode() for c in [blkid] + objects])


class BlockWithoutCookie(obnam.exception.ExceptionBase):

    def __init__(self, block):
        self._msg = ("Block does not start with cookie: %s" %
                     " ".join("%02x" % ord(c) for c in block[:32]))


def block_decode(block):
    """Return list of decoded components in block, or None on error"""
    if block.startswith(BLOCK_COOKIE):
        parser = obnam.cmp.Parser(block, len(BLOCK_COOKIE))
        return parser.decode_all()
    else:
        raise BlockWithoutCookie(block)


class SignatureObject(StorageObject):

    kind = SIG

    def __init__(self, components=None, id=None, sigdata=None):
        StorageObject.__init__(self, components=components, id=id)
        if sigdata:
            c = obnam.cmp.Component(obnam.cmp.SIGDATA, sigdata)
            self.add(c)


class DeltaObject(StorageObject):

    kind = DELTA

    def __init__(self, components=None, id=id, deltapart_refs=None, 
                 cont_ref=None, delta_ref=None):
        StorageObject.__init__(self, components=components, id=id)
        for deltapart_ref in deltapart_refs:
            c = obnam.cmp.Component(obnam.cmp.DELTAPARTREF, deltapart_ref)
            self.add(c)
        if cont_ref:
            c = obnam.cmp.Component(obnam.cmp.CONTREF, cont_ref)
            self.add(c)
        elif delta_ref:
            c = obnam.cmp.Component(obnam.cmp.DELTAREF, delta_ref)
            self.add(c)


class GenerationObject(StorageObject):

    kind = GEN

    def __init__(self, components=None, id=None, filelist_id=None, 
                 dirrefs=None, filegrouprefs=None, start=None, end=None):
        StorageObject.__init__(self, components=components, id=id)
        if filelist_id:
            self.add(obnam.cmp.Component(obnam.cmp.FILELISTREF, filelist_id))
        for ref in dirrefs:
            self.add(obnam.cmp.Component(obnam.cmp.DIRREF, ref))
        for ref in filegrouprefs:
            self.add(obnam.cmp.Component(obnam.cmp.FILEGROUPREF, ref))
        if start:
            self.add(obnam.cmp.Component(obnam.cmp.GENSTART, 
                                         obnam.varint.encode(start)))
        if end:
            self.add(obnam.cmp.Component(obnam.cmp.GENEND, 
                                         obnam.varint.encode(end)))

    def get_filelistref(self):
        return self.first_string_by_kind(obnam.cmp.FILELISTREF)

    def get_dirrefs(self):
        return self.find_strings_by_kind(obnam.cmp.DIRREF)

    def get_filegrouprefs(self):
        return self.find_strings_by_kind(obnam.cmp.FILEGROUPREF)

    def get_start_time(self):
        return self.first_varint_by_kind(obnam.cmp.GENSTART)

    def get_end_time(self):
        return self.first_varint_by_kind(obnam.cmp.GENEND)


# This is used only by testing.
def generation_object_decode(gen):
    """Decode a generation object into objid, file list ref"""

    o = decode(gen)
    return o.get_id(), \
           o.first_string_by_kind(obnam.cmp.FILELISTREF), \
           o.find_strings_by_kind(obnam.cmp.DIRREF), \
           o.find_strings_by_kind(obnam.cmp.FILEGROUPREF), \
           o.first_varint_by_kind(obnam.cmp.GENSTART), \
           o.first_varint_by_kind(obnam.cmp.GENEND)


class HostBlockObject(StorageObject):

    kind = HOST

    def __init__(self, components=None, host_id=None, gen_ids=None, 
                 map_block_ids=None, contmap_block_ids=None):
        StorageObject.__init__(self, components=components, id=host_id)
        
        if components is None:
            c = obnam.cmp.Component(obnam.cmp.FORMATVERSION, FORMAT_VERSION)
            self.add(c)
    
        if gen_ids:
            for gen_id in gen_ids:
                c = obnam.cmp.Component(obnam.cmp.GENREF, gen_id)
                self.add(c)
    
        if map_block_ids:
            for map_block_id in map_block_ids:
                c = obnam.cmp.Component(obnam.cmp.MAPREF, map_block_id)
                self.add(c)
        
        if contmap_block_ids:
            for map_block_id in contmap_block_ids:
                c = obnam.cmp.Component(obnam.cmp.CONTMAPREF, map_block_id)
                self.add(c)
    
    def encode(self):
        oq = ObjectQueue()
        oq.add(self.get_id(), StorageObject.encode(self))
        return oq.as_block(self.get_id())


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


class DirObject(StorageObject):

    kind = DIR

    def __init__(self, components=None, id=None, name=None, stat=None, 
                 dirrefs=None, filegrouprefs=None):
        StorageObject.__init__(self, components=components, id=id)
        if name:
            self.add(obnam.cmp.Component(obnam.cmp.FILENAME, name))
        if stat:
            self.add(obnam.cmp.create_stat_component(stat))
        if dirrefs:
            for ref in dirrefs:
                self.add(obnam.cmp.Component(obnam.cmp.DIRREF, ref))
        if filegrouprefs:
            for ref in filegrouprefs:
                self.add(obnam.cmp.Component(obnam.cmp.FILEGROUPREF, ref))

    def get_name(self):
        return self.first_by_kind(obnam.cmp.FILENAME).get_string_value()

    def get_stat(self):
        st = self.first_by_kind(obnam.cmp.STAT)
        return obnam.cmp.parse_stat_component(st)

    def get_dirrefs(self):
        return [c.get_string_value() 
                for c in self.find_by_kind(obnam.cmp.DIRREF)]

    def get_filegrouprefs(self):
        return [c.get_string_value() 
                for c in self.find_by_kind(obnam.cmp.FILEGROUPREF)]


class FileGroupObject(StorageObject):

    kind = FILEGROUP

    def add_file(self, name, stat, contref, sigref, deltaref):
        c = obnam.filelist.create_file_component_from_stat(name, stat, 
                                                           contref, sigref, 
                                                           deltaref)
        self.add(c)

    def get_files(self):
        return self.find_by_kind(obnam.cmp.FILE)

    def get_file(self, name):
        for file in self.get_files():
            fname = obnam.cmp.first_string_by_kind(file.get_subcomponents(),
                                                   obnam.cmp.FILENAME)
            if name == fname:
                return file
        return None

    def get_string_from_file(self, file, kind):
        return obnam.cmp.first_string_by_kind(file.get_subcomponents(),
                                              kind)

    def get_stat_from_file(self, file):
        c = obnam.cmp.first_by_kind(file.get_subcomponents(), obnam.cmp.STAT)
        return obnam.cmp.parse_stat_component(c)

    def get_names(self):
        return [self.get_string_from_file(x, obnam.cmp.FILENAME) 
                for x in self.get_files()]

    def get_stat(self, filename):
        return self.get_stat_from_file(self.get_file(filename))

    def get_contref(self, filename):
        return self.get_string_from_file(self.get_file(filename),
                                         obnam.cmp.CONTREF)

    def get_sigref(self, filename):
        return self.get_string_from_file(self.get_file(filename),
                                         obnam.cmp.SIGREF)

    def get_deltaref(self, filename):
        return self.get_string_from_file(self.get_file(filename),
                                         obnam.cmp.DELTAREF)


class FileListObject(StorageObject):

    kind = FILELIST


class FilePartObject(StorageObject):

    kind = FILEPART


class FileContentsObject(StorageObject):

    kind = FILECONTENTS


class DeltaPartObject(StorageObject):

    kind = DELTAPART



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
        kind = obnam.cmp.first_varint_by_kind(components, obnam.cmp.OBJKIND)
        for klass in self._classes:
            if klass.kind == kind:
                return klass(components=components)
        return None
