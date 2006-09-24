from wibbrlib.varint import *


# Constants for component types
_next_component_id = 1
def _get_component_id():
    global _next_component_id
    x = _next_component_id
    _next_component_id += 1
    return x
CMP_OBJID = _get_component_id()
CMP_OBJTYPE = _get_component_id()
CMP_BLKID = _get_component_id()
CMP_FILEDATA = _get_component_id()
CMP_OBJPART = _get_component_id()
CMP_OBJMAP = _get_component_id()
CMP_ST_MODE = _get_component_id()
CMP_ST_INO = _get_component_id()
CMP_ST_DEV = _get_component_id()
CMP_ST_NLINK = _get_component_id()
CMP_ST_UID = _get_component_id()
CMP_ST_GID = _get_component_id()
CMP_ST_SIZE = _get_component_id()
CMP_ST_ATIME = _get_component_id()
CMP_ST_MTIME = _get_component_id()
CMP_ST_CTIME = _get_component_id()
CMP_ST_BLOCKS = _get_component_id()
CMP_ST_BLKSIZE = _get_component_id()
CMP_ST_RDEV = _get_component_id()
CMP_CONTREF = _get_component_id()
CMP_NAMEIPAIR = _get_component_id()
CMP_INODEREF = _get_component_id()
CMP_FILENAME = _get_component_id()
CMP_SIGDATA = _get_component_id()
CMP_SIGREF = _get_component_id()


_component_type_to_name = {
    CMP_OBJID: "CMP_OBJID",
    CMP_OBJTYPE: "CMP_OBJTYPE",
    CMP_BLKID: "CMP_BLKID",
    CMP_FILEDATA: "CMP_FILEDATA",
    CMP_OBJPART: "CMP_OBJPART",
    CMP_OBJMAP: "CMP_OBJMAP",
    CMP_ST_MODE: "CMP_ST_MODE",
    CMP_ST_INO: "CMP_ST_INO",
    CMP_ST_DEV: "CMP_ST_DEV",
    CMP_ST_NLINK: "CMP_ST_NLINK",
    CMP_ST_UID: "CMP_ST_UID",
    CMP_ST_GID: "CMP_ST_GID",
    CMP_ST_SIZE: "CMP_ST_SIZE",
    CMP_ST_ATIME: "CMP_ST_ATIME",
    CMP_ST_MTIME: "CMP_ST_MTIME",
    CMP_ST_CTIME: "CMP_ST_CTIME",
    CMP_ST_BLOCKS: "CMP_ST_BLOCKS",
    CMP_ST_BLKSIZE: "CMP_ST_BLKSIZE",
    CMP_ST_RDEV: "CMP_ST_RDEV",
    CMP_CONTREF: "CMP_CONTREF",
    CMP_NAMEIPAIR: "CMP_NAMEIPAIR",
    CMP_INODEREF: "CMP_INODEREF",
    CMP_FILENAME: "CMP_FILENAME",
    CMP_SIGDATA: "CMP_SIGDATA",
    CMP_SIGREF: "CMP_SIGREF",
}


def component_type_name(type):
    """Return a textual name for a numeric component type"""
    return _component_type_to_name.get(type, "CMP_UNKNOWN")


def component_encode(type, data):
    """Encode a component as a string"""
    return varint_encode(len(data)) + varint_encode(type) + data


def component_decode(str, pos):
    """Decode an encoded component, return type, data, and pos after it"""
    (size, pos) = varint_decode(str, pos)
    (type, pos) = varint_decode(str, pos)
    data = str[pos:pos+size]
    return type, data, pos + size
