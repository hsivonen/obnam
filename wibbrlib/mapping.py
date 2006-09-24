def mapping_create():
    """Create a new object ID to block ID mapping"""
    return {}


def mapping_count(mapping):
    """Return the number of mappings in 'mapping'"""
    return len(mapping.keys())


def mapping_add(mapping, object_id, block_id):
    """Add a mapping from object_id to block_id"""
    if object_id in mapping:
        mapping[object_id].append(block_id)
    else:
        mapping[object_id] = [block_id]
