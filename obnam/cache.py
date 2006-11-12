"""Block cache for backup program"""


import os


class Cache:

    def __init__(self):
        self.cachedir = None


def init(config):
    """Initialize cache subsystem, return opaque cache object"""
    cache = Cache()
    cache.cachedir = config.get("backup", "cache-dir")
    if not os.path.isdir(cache.cachedir):
        os.makedirs(cache.cachedir, 0700)
    return cache


def cache_pathname(cache, block_id):
    """Return pathname in local block cache for a given block id"""
    return os.path.join(cache.cachedir, block_id)


def _create_new_cache_file(cache, block_id):
    """Create a new file in the local block cache, and open it for writing"""
    pathname = cache_pathname(cache, block_id)
    dirname = os.path.dirname(pathname)
    if not os.path.isdir(dirname):
        os.makedirs(dirname, 0700)
    return file(pathname + ".new", "w", 0600)


def _close_new_cache_file(cache, block_id, f):
    """Close a file opened by _open_cache_file"""
    f.close()
    pathname = cache_pathname(cache, block_id)
    os.rename(pathname + ".new", pathname)


def put_block(cache, block_id, block):
    """Put a block into the cache"""
    f = _create_new_cache_file(cache, block_id)
    f.write(block)
    _close_new_cache_file(cache, block_id, f)


def get_block(cache, block_id):
    """Return the contents of a block in the block cache, None if not there"""
    try:
        f = file(cache_pathname(cache, block_id), "r")
        block = f.read()
        f.close()
    except IOError, e:
        return None
    return block
