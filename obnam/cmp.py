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


"""Obnam data components"""


import obnam


# Constants for component kinds

_component_kinds = {}

COMPOSITE_FLAG = 0x01
REF_FLAG = 0x02

def _define_kind(code, is_composite, is_ref, name):
    code = code << 2
    if is_composite:
        code = code | COMPOSITE_FLAG
    if is_ref:
        code = code | REF_FLAG
    assert code not in _component_kinds
    assert is_composite in [True, False]
    assert is_ref in [True, False]
    assert (is_composite, is_ref) != (True, True)
    assert name not in _component_kinds.values()
    _component_kinds[code] = (is_composite, name)
    return code

def _define_composite(code, name):
    return _define_kind(code, True, False, name)

def _define_ref(code, name):
    return _define_kind(code, False, True, name)

def _define_plain(code, name):
    return _define_kind(code, False, False, name)

OBJID         = _define_plain(       1, "OBJID")
OBJKIND       = _define_plain(       2, "OBJKIND")
BLKID         = _define_plain(       3, "BLKID")
FILECHUNK     = _define_plain(       4, "FILECHUNK")
OBJECT        = _define_composite(   5, "OBJECT")
OBJMAP        = _define_composite(   6, "OBJMAP")
# 7-19 have been obsoleted and should not exist anywhere in the universe.
CONTREF       = _define_ref(        20, "CONTREF")
NAMEIPAIR     = _define_composite(  21, "NAMEIPAIR")
# 22 has been obsoleted and should not exist anywhere in the universe.
FILENAME      = _define_plain(      23, "FILENAME")
SIGDATA       = _define_plain(      24, "SIGDATA")
SIGREF        = _define_ref(        25, "SIGREF")
GENREF        = _define_ref(        26, "GENREF")
OBJREF        = _define_ref(        28, "OBJREF")
BLOCKREF      = _define_ref(        29, "BLOCKREF")
MAPREF        = _define_ref(        30, "MAPREF")
FILEPARTREF   = _define_ref(        31, "FILEPARTREF")
FORMATVERSION = _define_plain(      32, "FORMATVERSION")
FILE          = _define_composite(  33, "FILE")
FILELISTREF   = _define_ref(        34, "FILELISTREF")
CONTMAPREF    = _define_ref(        35, "CONTMAPREF")
DELTAREF      = _define_ref(        36, "DELTAREF")
DELTADATA     = _define_plain(      37, "DELTADATA")
STAT          = _define_plain(      38, "STAT")
GENSTART      = _define_plain(      39, "GENSTART")
GENEND        = _define_plain(      40, "GENEND")
DELTAPARTREF  = _define_ref(        41, "DELTAPARTREF")
DIRREF        = _define_ref(        42, "DIRREF")
FILEGROUPREF  = _define_ref(        43, "FILEGROUPREF")


def kind_name(kind):
    """Return a textual name for a numeric component kind"""
    if kind in _component_kinds:
        return _component_kinds[kind][1]
    else:
        return "UNKNOWN"


def kind_is_composite(kind):
    """Is a kind supposed to be composite?"""
    if kind in _component_kinds:
        return _component_kinds[kind][0]
    else:
        return False


def kind_is_reference(kind):
    """Is a kind a reference to an object?"""
    if kind & REF_FLAG:
        return True
    else:
        return False


class Component:

    def __init__(self, kind, value):
        self.kind = kind
        assert type(value) in [type(""), type([])]
        if type(value) == type(""):
            self.str = value
            self.subcomponents = []
        else:
            self.str = None
            for x in value:
                assert isinstance(x, Component)
            self.subcomponents = value[:]

    def get_kind(self):
        """Return kind kind of a component"""
        return self.kind

    def get_string_value(self):
        """Return string value of leaf component"""
        assert self.str is not None
        return self.str

    def get_varint_value(self):
        """Return integer value of leaf component"""
        assert self.str is not None
        return obnam.varint.decode(self.str, 0)[0]

    def get_subcomponents(self):
        """Return list of subcomponents of composite component"""
        assert self.str is None
        return self.subcomponents

    def is_composite(self):
        """Is a component a leaf component or a composite one?"""
        return self.str is None

    def find_by_kind(self, wanted_kind):
        """Find subcomponents of a desired kind"""
        return [c for c in self.subcomponents if c.get_kind() == wanted_kind]
    
    def first_by_kind(self, wanted_kind):
        """Find first subcomponent of a desired kind"""
        for c in self.subcomponents:
            if c.get_kind() == wanted_kind:
                return c
        return None

    def find_strings_by_kind(self, wanted_kind):
        """Find subcomponents by kind, return their string values"""
        return [c.get_string_value() 
                for c in find_by_kind(self.subcomponents, wanted_kind)]

    def first_string_by_kind(self, wanted_kind):
        """Find first subcomponent by kind, return its string value"""
        c = self.first_by_kind(wanted_kind)
        if c:
            return c.get_string_value()
        else:
            return None

    def first_varint_by_kind(self, wanted_kind):
        """Find first subcomponent by kind, return its integer value"""
        c = self.first_by_kind(wanted_kind)
        if c:
            return c.get_varint_value()
        else:
            return None

    def encode(self):
        """Encode a component as a string"""
        if self.is_composite():
            snippets = []
            for sub in self.get_subcomponents():
                snippets.append(sub.encode())
            encoded = "".join(snippets)
        else:
            encoded = self.str
        return "%s%s%s" % (obnam.varint.encode(len(encoded)),
                           obnam.varint.encode(self.kind),
                           encoded)


class Parser:

    def __init__(self, encoded, pos=0, end=None):
        self.encoded = encoded
        self.pos = pos
        if end is None or end > len(encoded):
            self.end = len(encoded)
        else:
            self.end = end
        
    def decode(self):
        """Parse one component, and its value if type is composite"""
        if self.pos >= self.end:
            return None

        size, self.pos = obnam.varint.decode(self.encoded, self.pos)
        kind, self.pos = obnam.varint.decode(self.encoded, self.pos)
        
        if kind_is_composite(kind):
            parser = Parser(self.encoded, self.pos, self.pos + size)
            value = parser.decode_all()
        else:
            value = self.encoded[self.pos:self.pos + size]

        self.pos += size

        return Component(kind, value)

    def decode_all(self):
        """Decode all remaining components and values"""
        list = []
        while True:
            c = self.decode()
            if c is None:
                break
            list.append(c)
        return list


def find_by_kind(components, wanted_kind):
    """Find components of a desired kind in a list of components"""
    return [c for c in components if c.get_kind() == wanted_kind]


def first_by_kind(components, wanted_kind):
    """Find first component of a desired kind in a list of components"""
    for c in components:
        if c.get_kind() == wanted_kind:
            return c
    return None


def find_strings_by_kind(components, wanted_kind):
    """Find components by kind, return their string values"""
    return [c.get_string_value() 
            for c in find_by_kind(components, wanted_kind)]


def first_string_by_kind(components, wanted_kind):
    """Find first component by kind, return its string value"""
    c = first_by_kind(components, wanted_kind)
    if c:
        return c.get_string_value()
    else:
        return None


def first_varint_by_kind(components, wanted_kind):
    """Find first component by kind, return its integer value"""
    c = first_by_kind(components, wanted_kind)
    if c:
        return c.get_varint_value()
    else:
        return None


def create_stat_component(st):
    """Create a STAT component, given a stat result"""
    return Component(obnam.cmp.STAT,
                     obnam.varint.encode(st.st_mode) +
                     obnam.varint.encode(st.st_ino) +
                     obnam.varint.encode(st.st_dev) +
                     obnam.varint.encode(st.st_nlink) +
                     obnam.varint.encode(st.st_uid) +
                     obnam.varint.encode(st.st_gid) +
                     obnam.varint.encode(st.st_size) +
                     obnam.varint.encode(st.st_atime) +
                     obnam.varint.encode(st.st_mtime) +
                     obnam.varint.encode(st.st_ctime) +
                     obnam.varint.encode(st.st_blocks) +
                     obnam.varint.encode(st.st_blksize) +
                     obnam.varint.encode(st.st_rdev))


def parse_stat_component(stat_component):
    """Return an object like a stat result from a decoded stat_component"""
    value = stat_component.get_string_value()
    pos = 0
    st_mode, pos = obnam.varint.decode(value, pos)
    st_ino, pos = obnam.varint.decode(value, pos)
    st_dev, pos = obnam.varint.decode(value, pos)
    st_nlink, pos = obnam.varint.decode(value, pos)
    st_uid, pos = obnam.varint.decode(value, pos)
    st_gid, pos = obnam.varint.decode(value, pos)
    st_size, pos = obnam.varint.decode(value, pos)
    st_atime, pos = obnam.varint.decode(value, pos)
    st_mtime, pos = obnam.varint.decode(value, pos)
    st_ctime, pos = obnam.varint.decode(value, pos)
    st_blocks, pos = obnam.varint.decode(value, pos)
    st_blksize, pos = obnam.varint.decode(value, pos)
    st_rdev, pos = obnam.varint.decode(value, pos)
    return obnam.utils.make_stat_result(st_mode=st_mode,
                                        st_ino=st_ino,
                                        st_dev=st_dev,
                                        st_nlink=st_nlink,
                                        st_uid=st_uid,
                                        st_gid=st_gid,
                                        st_size=st_size,
                                        st_atime=st_atime,
                                        st_mtime=st_mtime,
                                        st_ctime=st_ctime,
                                        st_blocks=st_blocks,
                                        st_blksize=st_blksize,
                                        st_rdev=st_rdev)
