import uuid

from wibbrlib.exception import WibbrException
from wibbrlib.component import *


# Constants of object types

_object_types = {}

def _define_type(code, name):
    assert code not in _object_types
    assert name not in _object_types.values()
    _object_types[code] = name
    return code

OBJ_FILECONT    = _define_type(1, "OBJ_FILECONT")
OBJ_INODE       = _define_type(2, "OBJ_INODE")
OBJ_GEN         = _define_type(3, "OBJ_GEN")
OBJ_SIG         = _define_type(4, "OBJ_SIG")


def object_type_name(type):
    """Return a textual name for a numeric object type"""
    return _object_types.get(type, "OBJ_UNKNOWN")


def object_id_new():
    """Return a string that is a universally unique ID for an object"""
    return str(uuid.uuid4())


def object_encode(objid, objtype, encoded_components):
    """Encode an object, given id, type, and list of encoded components"""
    objid = component_encode(CMP_OBJID, objid)
    objtype = component_encode(CMP_OBJTYPE, varint_encode(objtype))
    return objid + objtype + "".join(encoded_components)


def object_decode(str, pos):
    """Decode an object, return components as list of (type, data)"""
    pairs = []
    while pos < len(str):
        (type, data, pos) = component_decode(str, pos)
        if type == CMP_OBJTYPE:
            (data, _) = varint_decode(data, 0)
        pairs.append((type, data))
    return pairs


def object_queue_create():
    """Create an empty object queue"""
    return []


def object_queue_add(oq, object):
    """Add an encoded object into an object queue"""
    oq.append(object)


def object_queue_combined_size(oq):
    """Return the combined size of all objects in an object queue"""
    return sum([len(x) for x in oq])


def block_create_from_object_queue(blkid, oq):
    """Create a block from an object queue"""
    blkid = component_encode(CMP_BLKID, blkid)
    objects = [component_encode(CMP_OBJPART, x) for x in oq]
    return blkid + "".join(objects)


def normalize_stat_result(stat_result):
    """Create a new, normalized object from the return value of os.stat
    
    The normalized value has the st_xxx fields that the return value of
    os.stat has, but two normalized values may be safely compared for
    equality. 
    
    """
    
    fields = [x for x in dir(stat_result) if x.startswith("st_")]
    o = {}
    for x in fields:
        o[x] = stat_result.__getattribute__(x)
    return o


def inode_object_encode(objid, stat_result, sig_id, contents_id):
    """Create an inode object from the return value of os.stat"""
    fields = []
    st = stat_result
    fields.append(component_encode(CMP_ST_MODE, varint_encode(st["st_mode"])))
    fields.append(component_encode(CMP_ST_INO, varint_encode(st["st_ino"])))
    fields.append(component_encode(CMP_ST_DEV, varint_encode(st["st_dev"])))
    fields.append(component_encode(CMP_ST_NLINK, varint_encode(st["st_nlink"])))
    fields.append(component_encode(CMP_ST_UID, varint_encode(st["st_uid"])))
    fields.append(component_encode(CMP_ST_GID, varint_encode(st["st_gid"])))
    fields.append(component_encode(CMP_ST_SIZE, varint_encode(st["st_size"])))
    fields.append(component_encode(CMP_ST_ATIME, varint_encode(st["st_atime"])))
    fields.append(component_encode(CMP_ST_MTIME, varint_encode(st["st_mtime"])))
    fields.append(component_encode(CMP_ST_CTIME, varint_encode(st["st_ctime"])))
    if "st_blocks" in st:
        fields.append(component_encode(CMP_ST_BLOCKS, 
                                       varint_encode(st["st_blocks"])))
    if "st_blksize" in st:
        fields.append(component_encode(CMP_ST_BLKSIZE, 
                                       varint_encode(st["st_blksize"])))
    if "st_rdev" in st:
        fields.append(component_encode(CMP_ST_RDEV, 
                                       varint_encode(st["st_rdev"])))
    fields.append(component_encode(CMP_SIGREF, sig_id))
    fields.append(component_encode(CMP_CONTREF, contents_id))
    return object_encode(objid, OBJ_INODE, fields)
    
    
class UnknownInodeField(WibbrException):

    def __init__(self, type):
        self._msg = "Unknown field in inode object: %d" % type


class NotAnInode(WibbrException):

    def __init__(self, otype):
        self._msg = "Object type is not inode: %d" % otype


def inode_object_decode(inode):
    """Decode an inode object, return objid and what os.stat returns"""
    pos = 0
    objid = None
    stat_results = {}
    sigref = None
    contref = None
    while pos < len(inode):
        (type, data, pos) = component_decode(inode, pos)
        if type == CMP_OBJID:
            objid = data
        elif type == CMP_OBJTYPE:
            (otype, _) = varint_decode(data, 0)
            if otype != OBJ_INODE:
                raise NotAnInode(otype)
        elif type == CMP_ST_MODE:
            stat_results["st_mode"] = varint_decode(data, 0)[0]
        elif type == CMP_ST_INO:
            stat_results["st_ino"] = varint_decode(data, 0)[0]
        elif type == CMP_ST_DEV:
            stat_results["st_dev"] = varint_decode(data, 0)[0]
        elif type == CMP_ST_NLINK:
            stat_results["st_nlink"] = varint_decode(data, 0)[0]
        elif type == CMP_ST_UID:
            stat_results["st_uid"] = varint_decode(data, 0)[0]
        elif type == CMP_ST_GID:
            stat_results["st_gid"] = varint_decode(data, 0)[0]
        elif type == CMP_ST_SIZE:
            stat_results["st_size"] = varint_decode(data, 0)[0]
        elif type == CMP_ST_ATIME:
            stat_results["st_atime"] = varint_decode(data, 0)[0]
        elif type == CMP_ST_MTIME:
            stat_results["st_mtime"] = varint_decode(data, 0)[0]
        elif type == CMP_ST_CTIME:
            stat_results["st_ctime"] = varint_decode(data, 0)[0]
        elif type == CMP_ST_BLOCKS:
            stat_results["st_blocks"] = varint_decode(data, 0)[0]
        elif type == CMP_ST_BLKSIZE:
            stat_results["st_blksize"] = varint_decode(data, 0)[0]
        elif type == CMP_ST_RDEV:
            stat_results["st_rdev"] = varint_decode(data, 0)[0]
        elif type == CMP_SIGREF:
            sigref = data
        elif type == CMP_CONTREF:
            contref = data
        else:
            raise UnknownInodeField(type)
    return objid, stat_results, sigref, contref


def generation_object_encode(objid, pairs):
    """Encode a generation object, from list of filename, inode_id pairs"""
    components = []
    for filename, inode_id in pairs:
        cf = component_encode(CMP_FILENAME, filename)
        ci = component_encode(CMP_INODEREF, inode_id)
        c = component_encode(CMP_NAMEIPAIR, cf + ci)
        components.append(c)
    return object_encode(objid, OBJ_GEN, components)


class UnknownGenerationComponent(WibbrException):

    def __init__(self, type):
        self._msg = "Unknown component in generation: %s (%d)" % \
            (component_type_name(type), type)


class NameInodePairHasTooManyComponents(WibbrException):

    def __init__(self):
        self._msg = "Name/inode pair has too many components"


class InvalidNameInodePair(WibbrException):

    def __init__(self):
        self._msg = "Name/inode pair does not consist of name and inode"


class WrongObjectType(WibbrException):

    def __init__(self, actual, wanted):
        self._msg = "Object is of type %s (%d), wanted %s (%d)" % \
            (object_type_name(actual), actual, 
             object_type_name(wanted), wanted)


def generation_object_decode(gen):
    """Decode a generation object into objid, list of name, inode_id pairs"""
    pos = 0
    objid = None
    pairs = []
    while pos < len(gen):
        (type, data, pos) = component_decode(gen, pos)
        if type == CMP_OBJID:
            objid = data
        elif type == CMP_OBJTYPE:
            (objtype, _) = varint_decode(data, 0)
            if objtype != OBJ_GEN:
                raise WrongObjectType(objtype, OBJ_GEN)
        elif type == CMP_NAMEIPAIR:
            (nitype1, nidata1, nipos) = component_decode(data, 0)
            (nitype2, nidata2, nipos) = component_decode(data, nipos)
            if nipos != len(data):
                raise NameInodePairHasTooManyComponents()
            if nitype1 == CMP_INODEREF and nitype2 == CMP_FILENAME:
                inode_id = nidata1
                filename = nidata2
            elif nitype2 == CMP_INODEREF and nitype1 == CMP_FILENAME:
                inode_id = nidata2
                filename = nidata1
            else:
                raise InvalidNameInodePair()
            pairs.append((filename, inode_id))
        else:
            raise UnknownGenerationComponent(type)
            
    return objid, pairs
