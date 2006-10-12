def encode(i):
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


def decode(str, pos):
    """Decode a varint from a string, return value and pos after it"""
    value = 0
    while pos < len(str):
        octet = ord(str[pos])
        value = (value << 7) | (octet & 0x7f)
        pos += 1
        if (octet & 0x80) == 0:
            break
    return value, pos


