import wibbrlib.component


class Mappings:

    def __init__(self):
        self.dict = {}
        self.new_keys = []


def create():
    """Create a new object ID to block ID mapping"""
    return Mappings()


def count(mapping):
    """Return the number of mappings in 'mapping'"""
    return len(mapping.dict.keys())


def add(mapping, object_id, block_id):
    """Add a mapping from object_id to block_id"""
    if object_id in mapping.dict:
        mapping.dict[object_id].append(block_id)
    else:
        mapping.dict[object_id] = [block_id]
        if object_id not in mapping.new_keys:
            mapping.new_keys.append(object_id)


def get(mapping, object_id):
    """Return the list of blocks, in order, that contain parts of an object"""
    return mapping.dict.get(object_id, None)


def get_new(mapping):
    """Return list of new mappings"""
    return mapping.new_keys


def reset_new(mapping):
    """Reset list of new mappings"""
    mapping.new_keys = []


def encode_new(mapping):
    """Return a list of encoded components for the new mappings"""
    list = []
    for key in get_new(mapping):
        objref = wibbrlib.component.create(wibbrlib.component.CMP_OBJREF, key)
        blockrefs = mapping.dict[key]
        blockrefs = [wibbrlib.component.create(
                        wibbrlib.component.CMP_BLOCKREF, x) 
                     for x in blockrefs]
        component = wibbrlib.component.create(wibbrlib.component.CMP_OBJMAP, 
                        [objref] + blockrefs)
        component = wibbrlib.component.encode(component)
        list.append(component)
    return list


def encode_new_to_block(mapping, block_id):
    """Encode new mappings into a block"""
    c = wibbrlib.component.create(wibbrlib.component.CMP_BLKID, block_id)
    list = encode_new(mapping)
    block = "".join([wibbrlib.component.encode(c)] + list)
    return block


def decode_block(mapping, mapping_block):
    """Decode a block with mappings, add them to mapping object"""
    list = wibbrlib.component.decode_all(mapping_block, 0)
    maps = wibbrlib.component.find_by_type(list, 
                                           wibbrlib.component.CMP_OBJMAP)
    for map in maps:
        object_id = None
        block_ids = []
        subs = wibbrlib.component.get_subcomponents(map)

        list = wibbrlib.component.find_by_type(subs, 
                                               wibbrlib.component.CMP_OBJREF)
        if len(list) == 1:
            object_id = wibbrlib.component.get_string_value(list[0])

        list = wibbrlib.component.find_by_type(subs, 
                                           wibbrlib.component.CMP_BLOCKREF)
        block_ids = [wibbrlib.component.get_string_value(c) for c in list]

        if object_id and block_ids:
            for block_id in block_ids:
                add(mapping, object_id, block_id)
