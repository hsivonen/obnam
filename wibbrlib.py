"""Library routines for wibbr, a backup program-"""


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
}


def component_type_name(type):
    """Return a textual name for a numeric component type"""
    return _component_type_to_name.get(type, "CMP_UNKNOWN")


# Constants of object types
OBJ_FILECONT = 1
OBJ_INODE = 2


_object_type_to_name = {
    OBJ_FILECONT: "OBJ_FILECONT",
    OBJ_INODE: "OBJ_INODE",
}


class WibbrException(Exception):

    def __str__(self):
        return self._msg


def object_type_name(type):
    """Return a textual name for a numeric object type"""
    return _object_type_to_name.get(type, "OBJ_UNKNOWN")


def varint_encode(i):
    """Encode an integer as a varint"""
    assert i >= 0
    if i == 0:
        return chr(0)
    else:
        septets = []
        while i > 0:
            octet = i & 0x7f
            if septets:
                octet = octet | 0x80
            septets.insert(0, chr(octet))
            i = i >> 7
        return "".join(septets)


def varint_decode(str, pos):
    """Decode a varint from a string, return value and pos after it"""
    value = 0
    while pos < len(str):
        octet = ord(str[pos])
        value = (value << 7) | (octet & 0x7f)
        pos += 1
        if (octet & 0x80) == 0:
            break
    return value, pos


def component_encode(type, data):
    """Encode a component as a string"""
    return varint_encode(len(data)) + varint_encode(type) + data


def component_decode(str, pos):
    """Decode an encoded component, return type, data, and pos after it"""
    (size, pos) = varint_decode(str, pos)
    (type, pos) = varint_decode(str, pos)
    data = str[pos:pos+size]
    return type, data, pos + size


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


def inode_object_encode(objid, stat_result, contents_id):
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
        elif type == CMP_CONTREF:
            contref = data
        else:
            raise UnknownInodeField(type)
    return objid, stat_results, contref
