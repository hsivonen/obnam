"""Library routines for wibbr, a backup program-"""


# Constants for component types
OBJID = 1
OBJTYPE = 2
BLKID = 3
FILEDATA = 4
OBJPART = 5
FILESIZE = 6
OBJMAP = 7


_component_type_to_name = {
    OBJID: "OBJID",
    OBJTYPE: "OBJTYPE",
    BLKID: "BLKID",
    FILEDATA: "FILEDATA",
    OBJPART: "OBJPART",
    FILESIZE: "FILESIZE",
    OBJMAP: "OBJMAP",
}


def component_type_name(type):
    """Return a textual name for a numeric component type"""
    return _component_type_to_name.get(type, "UNKNOWN")


# Constants of object types
FILECONT = 1
INODE = 2


_object_type_to_name = {
    FILECONT: "FILECONT",
    INODE: "INODE",
}


def object_type_name(type):
    """Return a textual name for a numeric object type"""
    return _object_type_to_name.get(type, "UNKNOWN")


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
    objid = component_encode(OBJID, objid)
    objtype = component_encode(OBJTYPE, varint_encode(objtype))
    return objid + objtype + "".join(encoded_components)


def object_decode(str, pos):
    """Decode an object, return components as list of (type, data)"""
    pairs = []
    while pos < len(str):
        (type, data, pos) = component_decode(str, pos)
        if type == OBJTYPE:
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
    blkid = component_encode(BLKID, blkid)
    objects = [component_encode(OBJPART, x) for x in oq]
    return blkid + "".join(objects)
