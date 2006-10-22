import wibbrlib.varint


# Constants for component types

_component_types = {}

def _define_type(code, is_composite, name):
    assert code not in _component_types
    assert is_composite in [True, False]
    assert name not in _component_types.values()
    _component_types[code] = (is_composite, name)
    return code


CMP_OBJID         = _define_type( 1, False, "CMP_OBJID")
CMP_OBJTYPE       = _define_type( 2, False, "CMP_OBJTYPE")
CMP_BLKID         = _define_type( 3, False, "CMP_BLKID")
CMP_FILECHUNK     = _define_type( 4, False, "CMP_FILECHUNK")
CMP_OBJECT        = _define_type( 5, True,  "CMP_OBJECT")
CMP_OBJMAP        = _define_type( 6, True,  "CMP_OBJMAP")
CMP_ST_MODE       = _define_type( 7, False, "CMP_ST_MODE")
CMP_ST_INO        = _define_type( 8, False, "CMP_ST_INO")
CMP_ST_DEV        = _define_type( 9, False, "CMP_ST_DEV")
CMP_ST_NLINK      = _define_type(10, False, "CMP_ST_NLINK")
CMP_ST_UID        = _define_type(11, False, "CMP_ST_UID")
CMP_ST_GID        = _define_type(12, False, "CMP_ST_GID")
CMP_ST_SIZE       = _define_type(13, False, "CMP_ST_SIZE")
CMP_ST_ATIME      = _define_type(14, False, "CMP_ST_ATIME")
CMP_ST_MTIME      = _define_type(15, False, "CMP_ST_MTIME")
CMP_ST_CTIME      = _define_type(16, False, "CMP_ST_CTIME")
CMP_ST_BLOCKS     = _define_type(17, False, "CMP_ST_BLOCKS")
CMP_ST_BLKSIZE    = _define_type(18, False, "CMP_ST_BLKSIZE")
CMP_ST_RDEV       = _define_type(19, False, "CMP_ST_RDEV")
CMP_CONTREF       = _define_type(20, False, "CMP_CONTREF")
CMP_NAMEIPAIR     = _define_type(21, True,  "CMP_NAMEIPAIR")
CMP_INODEREF      = _define_type(22, False, "CMP_INODEREF")
CMP_FILENAME      = _define_type(23, False, "CMP_FILENAME")
CMP_SIGDATA       = _define_type(24, False, "CMP_SIGDATA")
CMP_SIGREF        = _define_type(25, False, "CMP_SIGREF")
CMP_GENREF        = _define_type(26, False, "CMP_GENREF")
CMP_OBJREF        = _define_type(28, False, "CMP_OBJREF")
CMP_BLOCKREF      = _define_type(29, False, "CMP_BLOCKREF")
CMP_MAPREF        = _define_type(30, False, "CMP_MAPREF")
CMP_FILEPARTREF   = _define_type(31, False, "CMP_FILEPARTREF")
CMP_FORMATVERSION = _define_type(32, False, "CMP_FORMATVERSION")


def type_name(type):
    """Return a textual name for a numeric component type"""
    if type in _component_types:
        return _component_types[type][1]
    else:
        return "CMP_UNKNOWN"


def type_is_composite(type):
    """Is a type supposed to be composite?"""
    if type in _component_types:
        return _component_types[type][0]
    else:
        return False


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


def get_varint_value(c):
    """Return integer value of leaf component"""
    assert c.str is not None
    return wibbrlib.varint.decode(c.str, 0)[0]


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
    return wibbrlib.varint.encode(len(encoded)) + \
           wibbrlib.varint.encode(c.type) + encoded


def decode(encoded, pos):
    """Decode a component in a string, return component and pos after it"""
    (size, pos) = wibbrlib.varint.decode(encoded, pos)
    (type, pos) = wibbrlib.varint.decode(encoded, pos)
    if type_is_composite(type):
        value = []
        pos2 = pos
        while pos2 < pos + size:
            (sub, pos2) = decode(encoded, pos2)
            value.append(sub)
    else:
        value = encoded[pos:pos+size]
    return create(type, value), pos + size


def decode_all(encoded, pos):
    """Return list of all components in a string"""
    list = []
    len_encoded = len(encoded)
    while pos < len_encoded:
        (c, pos) = decode(encoded, pos)
        list.append(c)
    return list


def find_by_type(components, wanted_type):
    """Find components of a desired type in a list of components"""
    return [c for c in components if get_type(c) == wanted_type]


def first_by_type(components, wanted_type):
    """Find first component of a desired type in a list of components"""
    for c in components:
        if get_type(c) == wanted_type:
            return c
    return None


def find_strings_by_type(components, wanted_type):
    """Find components by type, return their string values"""
    return [get_string_value(c) 
            for c in find_by_type(components, wanted_type)]


def first_string_by_type(components, wanted_type):
    """Find first component by type, return its string value"""
    c = first_by_type(components, wanted_type)
    if c:
        return get_string_value(c)
    else:
        return None


def first_varint_by_type(components, wanted_type):
    """Find first component by type, return its integer value"""
    c = first_by_type(components, wanted_type)
    if c:
        return get_varint_value(c)
    else:
        return None
