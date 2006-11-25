import obnam.cmp


class Mappings:

    def __init__(self):
        self.dict = {}
        self.new_keys = {}


def create():
    """Create a new object ID to block ID mapping"""
    return Mappings()


def count(mapping):
    """Return the number of mappings in 'mapping'"""
    return len(mapping.dict.keys())


def add(mapping, object_id, block_id):
    """Add a mapping from object_id to block_id"""
    _add_old(mapping, object_id, block_id)
    if object_id not in mapping.new_keys:
        mapping.new_keys[object_id] = 1


def _add_old(mapping, object_id, block_id):
    """Add a mapping from object_id to block_id"""
    assert object_id not in mapping.dict
    mapping.dict[object_id] = block_id


def get(mapping, object_id):
    """Return the list of blocks, in order, that contain parts of an object"""
    return mapping.dict.get(object_id, None)


def get_new(mapping):
    """Return list of new mappings"""
    return mapping.new_keys.keys()


def reset_new(mapping):
    """Reset list of new mappings"""
    mapping.new_keys = {}


def encode_new(mapping):
    """Return a list of encoded components for the new mappings"""
    list = []
    dict = {}
    for object_id in get_new(mapping):
        block_id = get(mapping, object_id)
        if block_id in dict:
            dict[block_id].append(object_id)
        else:
            dict[block_id] = [object_id]
    for block_id in dict:
        object_ids = dict[block_id]
        object_ids = [obnam.cmp.create(obnam.cmp.CMP_OBJREF, x)
                      for x in object_ids]
        block_id = obnam.cmp.create(obnam.cmp.CMP_BLOCKREF, block_id)
        c = obnam.cmp.create(obnam.cmp.CMP_OBJMAP, 
                                [block_id] + object_ids)
        list.append(obnam.cmp.encode(c))
    return list


def encode_new_to_block(mapping, block_id):
    """Encode new mappings into a block"""
    c = obnam.cmp.create(obnam.cmp.CMP_BLKID, block_id)
    list = encode_new(mapping)
    block = "".join([obnam.obj.BLOCK_COOKIE, obnam.cmp.encode(c)] + list)
    return block


def decode_block(mapping, mapping_block):
    """Decode a block with mappings, add them to mapping object"""
    list = obnam.obj.block_decode(mapping_block)
    maps = obnam.cmp.find_by_kind(list, obnam.cmp.CMP_OBJMAP)
    for map in maps:
        subs = obnam.cmp.get_subcomponents(map)
        block_id = obnam.cmp.first_string_by_kind(subs, 
                                               obnam.cmp.CMP_BLOCKREF)
        object_ids = obnam.cmp.find_strings_by_kind(subs, 
                                               obnam.cmp.CMP_OBJREF)
        if object_ids and block_id:
            for object_id in object_ids:
                _add_old(mapping, object_id, block_id)
