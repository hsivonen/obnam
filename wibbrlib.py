"""Library routines for wibbr, a backup program-"""


# Constants for component types
OBJID = 1
OBJTYPE = 2
BLKID = 3


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
