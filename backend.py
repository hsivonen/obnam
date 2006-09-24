"""Wibbr backend for communicating with the backup server.

This implementation only stores the stuff locally, however.

"""


import os

import uuid


class LocalBackEnd:

    def __init__(self):
        self.local_root = None
        self.block_cache_root = None
        self.curdir = None


def init(config):
    """Initialize the subsystem and return an opaque backend object"""
    be = LocalBackEnd()
    be.local_root = config.get("local-backend", "root")
    be.block_cache_root = config.get("wibbr", "block-cache")
    be.curdir = str(uuid.uuid4())
    return be


def generate_block_id(be):
    """Generate a new identifier for the block, when stored remotely"""
    return os.path.join(be.curdir, str(uuid.uuid4()))


def _block_remote_pathname(be, block_id):
    """Return pathname on server for a given block id"""
    return os.path.join(be.local_root, block_id)


def _block_cache_pathname(be, block_id):
    """Return pathname in local block cache for a given block id"""
    return os.path.join(be.block_cache_root, block_id)


def _open_cache_file(be, block_id):
    """Create a new file in the local block cache, and open it for writing"""
    pathname = _block_cache_pathname(be, block_id)
    dirname = os.path.dirname(pathname)
    if not os.path.isdir(dirname):
        os.makedirs(dirname, 0700)
    return file(pathname + ".new", "w", 0600)


def _close_cache_file(be, block_id, f):
    """Close a file opened by _open_cache_file"""
    f.close()
    pathname = _block_cache_pathname(be, block_id)
    os.rename(pathname + ".new", pathname)


def upload(be, block_id, block):
    """Start the upload of a block to the remote server"""
    curdir_full = os.path.join(be.local_root, be.curdir)
    if not os.path.isdir(curdir_full):
        os.makedirs(curdir_full, 0700)
    f = file(_block_remote_pathname(be, block_id), "w")
    f.write(block)
    f.close()
    return None


def download(be, block_id):
    """Download a block from the remote server, return success/failure"""
    try:
        f = file(_block_remote_pathname(be, block_id), "r")
        block = f.read()
        f.close()
        f = _open_cache_file(be, block_id)
        f.write(block)
        _close_cache_file(be, block_id, f)
    except IOError, e:
        return e
    return True
