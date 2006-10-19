"""Module for doing local file I/O and higher level remote operations"""


import os
import stat


import wibbrlib


def resolve(context, pathname):
    """Resolve a pathname relative to the user's desired target directory"""
    return os.path.join(context.config.get("wibbr", "target-dir"), pathname)


def unsolve(context, pathname):
    """Undo resolve(context, pathname)"""
    if pathname == os.sep:
        return pathname
    target = context.config.get("wibbr", "target-dir")
    if not target.endswith(os.sep):
        target += os.sep
    if pathname.startswith(target):
        return pathname[len(target):]
    else:
        return pathname


def flush_object_queue(context, oq):
    """Put all objects in an object queue into a block and upload it
    
    Also put mappings into map.
    
    """
    
    block_id = wibbrlib.backend.generate_block_id(context.be)
    block = wibbrlib.obj.block_create_from_object_queue(block_id, oq)
    wibbrlib.backend.upload(context.be, block_id, block)
    for id in wibbrlib.obj.object_queue_ids(oq):
        wibbrlib.mapping.add(context.map, id, block_id)


def get_block(context, block_id):
    """Get a block from cache or by downloading it"""
    block = wibbrlib.cache.get_block(context.cache, block_id)
    if not block:
        e = wibbrlib.backend.download(context.be, block_id)
        if e:
            raise e
        block = wibbrlib.cache.get_block(context.cache, block_id)
    return block


class MissingBlock(wibbrlib.exception.WibbrException):

    def __init__(self, block_id, object_id):
        self._msg = "Block %s for object %s is missing" % \
                        (block_id, object_id)


def create_object_from_component_list(components):
    """Create a new object from a list of components"""
    list = wibbrlib.cmp.find_by_type(components, wibbrlib.cmp.CMP_OBJID)
    id = wibbrlib.cmp.get_string_value(list[0])
    
    list = wibbrlib.cmp.find_by_type(components, wibbrlib.cmp.CMP_OBJTYPE)
    type = wibbrlib.cmp.get_string_value(list[0])
    (type, _) = wibbrlib.varint.decode(type, 0)

    o = wibbrlib.obj.create(id, type)
    bad = (wibbrlib.cmp.CMP_OBJID, wibbrlib.cmp.CMP_OBJTYPE)
    for c in components:
        if wibbrlib.cmp.get_type(c) not in bad:
            wibbrlib.obj.add(o, c)
    return o

import os

class ObjectCache:

    def __init__(self):
        self.objects = {}
        self.mru = []
        if "WIBBR_OC_MAX" in os.environ:
            self.MAX = int(os.environ["WIBBR_OC_MAX"])
        else:
            self.MAX = 2000
        
    def get(self, object_id):
        if object_id in self.objects:
            self.mru.remove(object_id)
            self.mru.insert(0, object_id)
            return self.objects[object_id]
        else:
            return None
        
    def forget(self, object_id):
        if object_id in self.objects:
            del self.objects[object_id]
            self.mru.remove(object_id)
        
    def put(self, object):
        object_id = wibbrlib.obj.get_id(object)
        self.objects[object_id] = object
        self.mru.insert(0, object_id)
        while len(self.mru) >= self.MAX:
            self.forget(self.mru[-1])


object_cache = ObjectCache()


def get_object(context, object_id):
    """Fetch an object"""
    o = object_cache.get(object_id)
    if o:
        return o
        
    block_ids = wibbrlib.mapping.get(context.map, object_id)
    if not block_ids:
        return None

    block_id = block_ids[0]
    block = get_block(context, block_id)
    if not block:
        raise MissingBlock(block_id, object_id)

    list = wibbrlib.cmp.decode_all(block, 0)
    list = wibbrlib.cmp.find_by_type(list, wibbrlib.cmp.CMP_OBJPART)

    the_one = None
    for component in list:
        subs = wibbrlib.cmp.get_subcomponents(component)
        o = create_object_from_component_list(subs)
        if wibbrlib.obj.get_type(o) != wibbrlib.obj.OBJ_FILEPART:
            object_cache.put(o)
        if wibbrlib.obj.get_id(o) == object_id:
            the_one = o
    
#    for component in list:
#        subs = wibbrlib.cmp.get_subcomponents(component)
#        objids = wibbrlib.cmp.find_by_type(subs, wibbrlib.cmp.CMP_OBJID)
#        objids = [wibbrlib.cmp.get_string_value(x) for x in objids]
#        objids = [x for x in objids if x == object_id]
#        if objids:
#            o = create_object_from_component_list(subs)
#            if wibbrlib.obj.get_type(o) != wibbrlib.obj.OBJ_FILEPART:
#                object_cache.put(object_id, o)
#            return o
                
    return the_one


def upload_host_block(context, host_block):
    """Upload a host block"""
    return wibbrlib.backend.upload(context.be, 
                                   context.config.get("wibbr", "host-id"), 
                                   host_block)


def get_host_block(context):
    """Return (and fetch, if needed) the host block, or None if not found"""
    host_id = context.config.get("wibbr", "host-id")
    e = wibbrlib.backend.download(context.be, host_id)
    if e:
        raise e
    return wibbrlib.cache.get_block(context.cache, host_id)


def enqueue_object(context, object_id, object):
    """Put an object into the object queue, and flush queue if too big"""
    oq = context.oq
    block_size = context.config.getint("wibbr", "block-size")
    cur_size = wibbrlib.obj.object_queue_combined_size(oq)
    if len(object) + cur_size > block_size:
        wibbrlib.io.flush_object_queue(context, oq)
        wibbrlib.obj.object_queue_clear(oq)
    wibbrlib.obj.object_queue_add(oq, object_id, object)


def create_file_contents_object(context, filename):
    """Create and queue objects to hold a file's contents"""
    object_id = wibbrlib.obj.object_id_new()
    part_ids = []
    block_size = context.config.getint("wibbr", "block-size")
    f = file(resolve(context, filename), "r")
    while True:
        data = f.read(block_size)
        if not data:
            break
        c = wibbrlib.cmp.create(wibbrlib.cmp.CMP_FILECHUNK, data)
        part_id = wibbrlib.obj.object_id_new()
        o = wibbrlib.obj.create(part_id, wibbrlib.obj.OBJ_FILEPART)
        wibbrlib.obj.add(o, c)
        o = wibbrlib.obj.encode(o)
        enqueue_object(context, part_id, o)
        part_ids.append(part_id)
    f.close()

    o = wibbrlib.obj.create(object_id, wibbrlib.obj.OBJ_FILECONTENTS)
    for part_id in part_ids:
        c = wibbrlib.cmp.create(wibbrlib.cmp.CMP_FILEPARTREF, part_id)
        wibbrlib.obj.add(o, c)
    o = wibbrlib.obj.encode(o)
    enqueue_object(context, object_id, o)

    return object_id


class FileContentsObjectMissing(wibbrlib.exception.WibbrException):

    def __init__(self, id):
        self._msg = "Missing file contents object: %s" % id


def get_file_contents(context, fd, cont_id):
    """Write contents of a file in backup to a file descriptor"""
    cont = wibbrlib.io.get_object(context, cont_id)
    if not cont:
        raise FileContentsObjectMissing(cont_id)
    part_ids = wibbrlib.obj.find_strings_by_type(cont, 
                                              wibbrlib.cmp.CMP_FILEPARTREF)
    for part_id in part_ids:
        part = wibbrlib.io.get_object(context, part_id)
        chunk = wibbrlib.obj.first_string_by_type(part, 
                                                  wibbrlib.cmp.CMP_FILECHUNK)
        os.write(fd, chunk)


def set_inode(full_pathname, inode):
    mode = wibbrlib.obj.first_varint_by_type(inode, wibbrlib.cmp.CMP_ST_MODE)
    atime = wibbrlib.obj.first_varint_by_type(inode, wibbrlib.cmp.CMP_ST_ATIME)
    mtime = wibbrlib.obj.first_varint_by_type(inode, wibbrlib.cmp.CMP_ST_MTIME)
    os.utime(full_pathname, (atime, mtime))
    os.chmod(full_pathname, stat.S_IMODE(mode))
