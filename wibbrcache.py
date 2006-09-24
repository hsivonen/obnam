"""Block cache for wibbr"""


import os


class Cache:

    def __init__(self):
        self.cachedir = None


def init(config):
    """Initialize cache subsystem, return opaque cache object"""
    cache = Cache()
    cache.cachedir = config.get("wibbr", "block-cache")
    if not os.path.isdir(cache.cachedir):
        os.makedirs(cache.cachedir, 0700)
    return cache
