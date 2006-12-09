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


"""Obnam data components"""


import obnam.varint


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
ST_MODE       = _define_plain(       7, "ST_MODE")
ST_INO        = _define_plain(       8, "ST_INO")
ST_DEV        = _define_plain(       9, "ST_DEV")
ST_NLINK      = _define_plain(      10, "ST_NLINK")
ST_UID        = _define_plain(      11, "ST_UID")
ST_GID        = _define_plain(      12, "ST_GID")
ST_SIZE       = _define_plain(      13, "ST_SIZE")
ST_ATIME      = _define_plain(      14, "ST_ATIME")
ST_MTIME      = _define_plain(      15, "ST_MTIME")
ST_CTIME      = _define_plain(      16, "ST_CTIME")
ST_BLOCKS     = _define_plain(      17, "ST_BLOCKS")
ST_BLKSIZE    = _define_plain(      18, "ST_BLKSIZE")
ST_RDEV       = _define_plain(      19, "ST_RDEV")
CONTREF       = _define_ref(        20, "CONTREF")
NAMEIPAIR     = _define_composite(  21, "NAMEIPAIR")
INODEREF      = _define_ref(        22, "INODEREF")
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
    """Is a kind supposed to be composite?"""
    if kind & REF_FLAG:
        return True
    else:
        return False


class Component:

    def __init__(self):
        self.kind = None
        self.str = None
        self.subcomponents = []


def create(component_kind, value):
    """Create a new component
    
    'value' must be either a string (for a leaf component) or a list
    of component values.
    
    """

    assert type(value) in [type(""), type([])]
    c = Component()
    c.kind = component_kind
    if type(value) == type(""):
        c.str = value
    else:
        for x in value:
            assert type(x) == type(c)
        c.subcomponents = value[:]
    return c


def get_kind(c):
    """Return kind kind of a component"""
    return c.kind


def get_string_value(c):
    """Return string value of leaf component"""
    assert c.str is not None
    return c.str


def get_varint_value(c):
    """Return integer value of leaf component"""
    assert c.str is not None
    return obnam.varint.decode(c.str, 0)[0]


def get_subcomponents(c):
    """Return list of subcomponents of composite component"""
    assert c.str is None
    return c.subcomponents


def is_composite(c):
    """Is a component a leaf component or a composite one?"""
    return c.str is None


def encode(c):
    """Encode a component as a string"""
    if is_composite(c):
        snippets = []
        for sub in get_subcomponents(c):
            snippets.append(encode(sub))
        encoded = "".join(snippets)
    else:
        encoded = c.str
    return obnam.varint.encode(len(encoded)) + \
           obnam.varint.encode(c.kind) + encoded


def decode(encoded, pos):
    """Decode a component in a string, return component and pos after it"""
    (size, pos) = obnam.varint.decode(encoded, pos)
    (kind, pos) = obnam.varint.decode(encoded, pos)
    if kind_is_composite(kind):
        value = []
        pos2 = pos
        while pos2 < pos + size:
            (sub, pos2) = decode(encoded, pos2)
            value.append(sub)
    else:
        value = encoded[pos:pos+size]
    return create(kind, value), pos + size


def decode_all(encoded, pos):
    """Return list of all components in a string"""
    list = []
    len_encoded = len(encoded)
    while pos < len_encoded:
        (c, pos) = decode(encoded, pos)
        list.append(c)
    return list


def find_by_kind(components, wanted_kind):
    """Find components of a desired kind in a list of components"""
    return [c for c in components if get_kind(c) == wanted_kind]


def first_by_kind(components, wanted_kind):
    """Find first component of a desired kind in a list of components"""
    for c in components:
        if get_kind(c) == wanted_kind:
            return c
    return None


def find_strings_by_kind(components, wanted_kind):
    """Find components by kind, return their string values"""
    return [get_string_value(c) 
            for c in find_by_kind(components, wanted_kind)]


def first_string_by_kind(components, wanted_kind):
    """Find first component by kind, return its string value"""
    c = first_by_kind(components, wanted_kind)
    if c:
        return get_string_value(c)
    else:
        return None


def first_varint_by_kind(components, wanted_kind):
    """Find first component by kind, return its integer value"""
    c = first_by_kind(components, wanted_kind)
    if c:
        return get_varint_value(c)
    else:
        return None
