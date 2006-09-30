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
