"""Wibbr backend for communicating with the backup server.

This implementation only stores the stuff locally, however.

"""


import os

import uuid


class LocalBackEnd:

    def __init__(self):
        self.local_root = None
        self.curdir = None


def init(config):
    """Initialize the subsystem and return an opaque backend object"""
    be = LocalBackEnd()
    be.local_root = config.get("local-backend", "root")
    be.curdir = str(uuid.uuid4())
    return be


def generate_block_id(be):
    """Generate a new identifier for the block, when stored remotely"""
    return os.path.join(be.curdir, str(uuid.uuid4()))


def upload(be, block_id, block):
    """Start the upload of a block to the remote server"""
    curdir_full = os.path.join(be.local_root, be.curdir)
    if not os.path.isdir(curdir_full):
        os.makedirs(curdir_full, 0700)
    block_pathname = os.path.join(be.local_root, block_id)
    f = file(block_pathname, "w")
    f.write(block)
    f.close()
    return None
