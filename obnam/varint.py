def encode(i):
    """Encode an integer as a varint"""
    return "%d\n" % i


def decode(encoded, pos):
    """Decode a varint from a string, return value and pos after it"""
    i = encoded.find("\n", pos)
    if i == -1:
        return -1, pos
    else:
        return int(encoded[pos:i]), i+1
