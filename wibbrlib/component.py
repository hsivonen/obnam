from wibbrlib.varint import *


# Constants for component types

_component_types = {}

def _define_type(code, name):
    assert code not in _component_types
    assert name not in _component_types.values()
    _component_types[code] = name
    return code


CMP_OBJID       = _define_type( 1, "CMP_OBJID")
CMP_OBJTYPE     = _define_type( 2, "CMP_OBJTYPE")
CMP_BLKID       = _define_type( 3, "CMP_BLKID")
CMP_FILECHUNK   = _define_type( 4, "CMP_FILECHUNK")
CMP_OBJPART     = _define_type( 5, "CMP_OBJPART")
CMP_OBJMAP      = _define_type( 6, "CMP_OBJMAP")
CMP_ST_MODE     = _define_type( 7, "CMP_ST_MODE")
CMP_ST_INO      = _define_type( 8, "CMP_ST_INO")
CMP_ST_DEV      = _define_type( 9, "CMP_ST_DEV")
CMP_ST_NLINK    = _define_type(10, "CMP_ST_NLINK")
CMP_ST_UID      = _define_type(11, "CMP_ST_UID")
CMP_ST_GID      = _define_type(12, "CMP_ST_GID")
CMP_ST_SIZE     = _define_type(13, "CMP_ST_SIZE")
CMP_ST_ATIME    = _define_type(14, "CMP_ST_ATIME")
CMP_ST_MTIME    = _define_type(15, "CMP_ST_MTIME")
CMP_ST_CTIME    = _define_type(16, "CMP_ST_CTIME")
CMP_ST_BLOCKS   = _define_type(17, "CMP_ST_BLOCKS")
CMP_ST_BLKSIZE  = _define_type(18, "CMP_ST_BLKSIZE")
CMP_ST_RDEV     = _define_type(19, "CMP_ST_RDEV")
CMP_CONTREF     = _define_type(20, "CMP_CONTREF")
CMP_NAMEIPAIR   = _define_type(21, "CMP_NAMEIPAIR")
CMP_INODEREF    = _define_type(22, "CMP_INODEREF")
CMP_FILENAME    = _define_type(23, "CMP_FILENAME")
CMP_SIGDATA     = _define_type(24, "CMP_SIGDATA")
CMP_SIGREF      = _define_type(25, "CMP_SIGREF")
CMP_GENREF      = _define_type(26, "CMP_GENREF")
CMP_GENLIST     = _define_type(27, "CMP_GENLIST")
CMP_OBJREF      = _define_type(28, "CMP_OBJREF")
CMP_BLOCKREF    = _define_type(29, "CMP_BLOCKREF")
CMP_MAPREF      = _define_type(30, "CMP_MAPREF")
CMP_FILEPARTREF = _define_type(31, "CMP_FILEPARTREF")


def component_type_name(type):
    """Return a textual name for a numeric component type"""
    return _component_types.get(type, "CMP_UNKNOWN")


class Component:

    def __init__(self):
        self.type = None
        self.str = None
        self.subcomponents = []


def create(component_type, value):
    """Create a new component
    
    'value' must be either a string (for a leaf component) or a list
    of component values.
    
    """
    assert component_type in _component_types
    assert type(value) in [type(""), type([])]
    c = Component()
    c.type = component_type
    if type(value) == type(""):
        c.str = value
    else:
        for x in value:
            assert type(x) == type(c)
        c.subcomponents = value[:]
    return c


def get_type(c):
    """Return type type of a component"""
    return c.type


def get_string_value(c):
    """Return string value of leaf component"""
    assert c.str is not None
    return c.str


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
    return varint_encode(len(encoded)) + varint_encode(c.type) + encoded


def component_encode(type, data):
    """Encode a component as a string"""
    return varint_encode(len(data)) + varint_encode(type) + data


def component_decode(str, pos):
    """Decode an encoded component, return type, data, and pos after it"""
    (size, pos) = varint_decode(str, pos)
    (type, pos) = varint_decode(str, pos)
    data = str[pos:pos+size]
    return type, data, pos + size

def component_decode_all(str, pos):
    """Return list of all components as (type, data) pairs in a string"""
    list = []
    while pos < len(str):
        (type, data, pos) = component_decode(str, pos)
        list.append((type, data))
    return list
