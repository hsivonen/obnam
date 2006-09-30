"""Wibbr backend for communicating with the backup server.

This implementation only stores the stuff locally, however.

"""


import os

import uuid
import wibbrlib.cache
import wibbrlib.mapping
import wibbrlib.object


class LocalBackEnd:

    def __init__(self):
        self.config = None
        self.local_root = None
        self.cache = None
        self.curdir = None


def init(config, cache):
    """Initialize the subsystem and return an opaque backend object"""
    be = LocalBackEnd()
    be.config = config
    be.local_root = config.get("wibbr", "local-store")
    be.cache = cache
    be.curdir = str(uuid.uuid4())
    return be


def generate_block_id(be):
    """Generate a new identifier for the block, when stored remotely"""
    return os.path.join(be.curdir, str(uuid.uuid4()))


def _block_remote_pathname(be, block_id):
    """Return pathname on server for a given block id"""
    return os.path.join(be.local_root, block_id)


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
    """Download a block from the remote server
    
    Return exception for error, or None for OK.
    
    """

    try:
        f = file(_block_remote_pathname(be, block_id), "r")
        block = f.read()
        f.close()
        wibbrlib.cache.put_block(be.cache, block_id, block)
    except IOError, e:
        return e
    return None


def list(be):
    """Return list of all files on the remote server"""
    list = []
    for dirpath, _, filenames in os.walk(be.local_root):
        list += [os.path.join(dirpath, x) for x in filenames]
    return list


def flush_object_queue(be, map, oq):
    """Put all objects in an object queue into a block and upload it
    
    Also put mappings into map.
    
    """
    
    block_id = generate_block_id(be)
    block = wibbrlib.object.block_create_from_object_queue(block_id, oq)
    upload(be, block_id, block)
    for id in wibbrlib.object.object_queue_ids(oq):
        wibbrlib.mapping.add(map, id, block_id)


def get_block(be, block_id):
    """Get a block from cache or by downloading it"""
    block = wibbrlib.cache.get_block(be.cache, block_id)
    if not block:
        e = download(be, block_id)
        if e:
            raise e
        block = wibbrlib.cache.get_block(be.cache, block_id)
    return block


class MissingBlock(wibbrlib.exception.WibbrException):

    def __init__(self, block_id, object_id):
        self._msg = "Block %s for object %s is missing" % \
                        (block_id, object_id)


def find_components_by_type(components, wanted_type):
    """Find all components of a given type"""
    return [x for x in components if x[0] == wanted_type]


def get_object(be, map, object_id):
    """Fetch an entire object, decoded into components"""
    object_components = []
    block_ids = wibbrlib.mapping.get(map, object_id)
    for block_id in block_ids:
        block = get_block(be, block_id)
        if not block:
            raise MissingBlock(block_id, object_id)
        list = wibbrlib.component.component_decode_all(block, 0)
        list = find_components_by_type(list, wibbrlib.component.CMP_OBJPART)
        list = [wibbrlib.component.component_decode_all(x[1], 0) for x in list]
        for components in list:
            objids = find_components_by_type(components,
                                             wibbrlib.component.CMP_OBJID)
            objids = [x for x in objids if x[1] == object_id]
            if objids:
                for i in range(len(components)):
                    if components[i][0] == wibbrlib.component.CMP_OBJTYPE:
                        type, data = components[i]
                        (data, _) = wibbrlib.varint.varint_decode(data, 0)
                        components[i] = (type, data)
                object_components += components
    return object_components


def upload_host_block(be, host_block):
    """Upload a host block"""
    return upload(be, be.config.get("wibbr", "host-id"), host_block)


def get_host_block(be):
    """Return (and fetch, if needed) the host block, or None if not found"""
    host_id = be.config.get("wibbr", "host-id")
    e = download(be, host_id)
    if e:
        raise e
    return wibbrlib.cache.get_block(be.cache, host_id)
