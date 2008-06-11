import sys

import obnamlib


def parse_components(data, pos, end):
    while pos < end:
        size, pos = obnamlib.varint.decode(data, pos)
        kind, pos = obnamlib.varint.decode(data, pos)
        yield size, kind, data[pos:pos+size]
        pos += size


def parse_object_kind(data):
    for size, kind, content in parse_components(data, 0, len(data)):
        if kind == obnamlib.cmp.OBJKIND:
            return obnamlib.varint.decode(content, 0)[0]
    return 0 # for unknown


def parse_object_sizes(data):
    assert data.startswith(obnamlib.obj.BLOCK_COOKIE)
    pos = len(obnamlib.obj.BLOCK_COOKIE)
    
    return [(size, parse_object_kind(content))
            for size, kind, content in parse_components(data, pos, len(data))
                if kind == obnamlib.cmp.OBJECT]


for filename in sys.argv[1:]:
    f = file(filename)
    data = f.read()
    f.close()
    for size, objkind in parse_object_sizes(data):
        print size, obnamlib.obj.kind_name(objkind)
