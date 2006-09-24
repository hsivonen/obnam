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
