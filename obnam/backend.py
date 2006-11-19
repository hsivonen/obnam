"""Backup program backend for communicating with the backup server.

This implementation only stores the stuff locally, however.

"""


import os
import urlparse

import uuid
import obnam.cache
import obnam.cmp
import obnam.mapping
import obnam.obj


MAX_BLOCKS_IN_CURDIR = 256


class BackendData:

    def __init__(self):
        self.config = None
        self.store = None
        self.cache = None
        self.curdir = None
        self.blocks_in_curdir = 0


def parse_store_url(url):
    """Parse a store url
    
    The url must either be a plain pathname, or it starts with sftp://
    and specifies a remote store. Return a tuple username, host, port,
    path, where elements can be None if they are meant to be the default
    or are not relevant.
    
    """
    
    # urlparse in Python 2.4 doesn't know, by default, that sftp uses
    # a netloc
    if "sftp" not in urlparse.uses_netloc:
        urlparse.uses_netloc.append("sftp")
    
    user = host = port = path = None
    (scheme, netloc, path, query, fragment) = urlparse.urlsplit(url)
    if False:
        print "scheme:", scheme
        print "netloc:", netloc
        print "path:", path
        print "query:", query
        print "fragment:", fragment
    
    if scheme == "sftp":
        host = netloc
    else:
        path = url
    
    return user, host, port, path


def init(config, cache):
    """Initialize the subsystem and return an opaque backend object"""
    be = BackendData()
    be.config = config
    be.store = config.get("backup", "store")
    be.cache = cache
    be.curdir = str(uuid.uuid4())
    return be


def generate_block_id(be):
    """Generate a new identifier for the block, when stored remotely"""
    if be.blocks_in_curdir >= MAX_BLOCKS_IN_CURDIR:
        be.curdir = str(uuid.uuid4())
        be.blocks_in_curdir = 1
    else:   
        be.blocks_in_curdir += 1
    return os.path.join(be.curdir, str(uuid.uuid4()))


def _block_remote_pathname(be, block_id):
    """Return pathname on server for a given block id"""
    return os.path.join(be.store, block_id)


def upload(be, block_id, block):
    """Start the upload of a block to the remote server"""
    curdir_full = os.path.join(be.store, be.curdir)
    if not os.path.isdir(curdir_full):
        os.makedirs(curdir_full, 0700)
    f = file(_block_remote_pathname(be, block_id), "w")
    f.write(block)
    f.close()
    return None


def download(be, block_id):
    """Download a block from the remote server
    
    Return exception for error, or None for OK.
    
    """

    try:
        f = file(_block_remote_pathname(be, block_id), "r")
        block = f.read()
        f.close()
        obnam.cache.put_block(be.cache, block_id, block)
    except IOError, e:
        return e
    return None


def list(be):
    """Return list of all files on the remote server"""
    list = []
    for dirpath, _, filenames in os.walk(be.store):
        if dirpath.startswith(be.store):
            dirpath = dirpath[len(be.store):]
            if dirpath.startswith(os.sep):
                dirpath = dirpath[len(os.sep):]
        list += [os.path.join(dirpath, x) for x in filenames]
    return list


def remove(be, block_id):
    """Remove a block from the remote server"""
    pathname = _block_remote_pathname(be, block_id)
    if os.path.exists(pathname):
        os.remove(pathname)
