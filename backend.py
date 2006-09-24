"""Wibbr backend for communicating with the backup server.

This implementation only stores the stuff locally, however.

"""


import uuid


class LocalBackEnd:

    def __init__(self):
        self.local_root = None


def init(config):
    """Initialize the subsystem and return an opaque backend object"""
    
    be = LocalBackEnd()
    be.local_root = config.get("local-backend", "root")
    return be
