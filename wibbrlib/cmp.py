import wibbrlib.varint


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

CMP_OBJID         = _define_plain(       1, "CMP_OBJID")
CMP_OBJKIND       = _define_plain(       2, "CMP_OBJKIND")
CMP_BLKID         = _define_plain(       3, "CMP_BLKID")
CMP_FILECHUNK     = _define_plain(       4, "CMP_FILECHUNK")
CMP_OBJECT        = _define_composite(   5, "CMP_OBJECT")
CMP_OBJMAP        = _define_composite(   6, "CMP_OBJMAP")
CMP_ST_MODE       = _define_plain(       7, "CMP_ST_MODE")
CMP_ST_INO        = _define_plain(       8, "CMP_ST_INO")
CMP_ST_DEV        = _define_plain(       9, "CMP_ST_DEV")
CMP_ST_NLINK      = _define_plain(      10, "CMP_ST_NLINK")
CMP_ST_UID        = _define_plain(      11, "CMP_ST_UID")
CMP_ST_GID        = _define_plain(      12, "CMP_ST_GID")
CMP_ST_SIZE       = _define_plain(      13, "CMP_ST_SIZE")
CMP_ST_ATIME      = _define_plain(      14, "CMP_ST_ATIME")
CMP_ST_MTIME      = _define_plain(      15, "CMP_ST_MTIME")
CMP_ST_CTIME      = _define_plain(      16, "CMP_ST_CTIME")
CMP_ST_BLOCKS     = _define_plain(      17, "CMP_ST_BLOCKS")
CMP_ST_BLKSIZE    = _define_plain(      18, "CMP_ST_BLKSIZE")
CMP_ST_RDEV       = _define_plain(      19, "CMP_ST_RDEV")
CMP_CONTREF       = _define_ref(        20, "CMP_CONTREF")
CMP_NAMEIPAIR     = _define_composite(  21, "CMP_NAMEIPAIR")
CMP_INODEREF      = _define_ref(        22, "CMP_INODEREF")
CMP_FILENAME      = _define_plain(      23, "CMP_FILENAME")
CMP_SIGDATA       = _define_plain(      24, "CMP_SIGDATA")
CMP_SIGREF        = _define_ref(        25, "CMP_SIGREF")
CMP_GENREF        = _define_ref(        26, "CMP_GENREF")
CMP_OBJREF        = _define_ref(        28, "CMP_OBJREF")
CMP_BLOCKREF      = _define_ref(        29, "CMP_BLOCKREF")
CMP_MAPREF        = _define_ref(        30, "CMP_MAPREF")
CMP_FILEPARTREF   = _define_ref(        31, "CMP_FILEPARTREF")
CMP_FORMATVERSION = _define_plain(      32, "CMP_FORMATVERSION")
CMP_FILE          = _define_composite(  33, "CMP_FILE")


def kind_name(kind):
    """Return a textual name for a numeric component kind"""
    if kind in _component_kinds:
        return _component_kinds[kind][1]
    else:
        return "CMP_UNKNOWN"


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
           wibbrlib.varint.encode(c.kind) + encoded


def decode(encoded, pos):
    """Decode a component in a string, return component and pos after it"""
    (size, pos) = wibbrlib.varint.decode(encoded, pos)
    (kind, pos) = wibbrlib.varint.decode(encoded, pos)
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
