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


def flush_object_queue(context, oq, map):
    """Put all objects in an object queue into a block and upload it
    
    Also put mappings into map.
    
    """
    
    if wibbrlib.obj.object_queue_combined_size(oq) > 0:
        block_id = wibbrlib.backend.generate_block_id(context.be)
        block = wibbrlib.obj.block_create_from_object_queue(block_id, oq)
        wibbrlib.backend.upload(context.be, block_id, block)
        for id in wibbrlib.obj.object_queue_ids(oq):
            wibbrlib.mapping.add(map, id, block_id)


def flush_all_object_queues(context):
    """Flush and clear all object queues in a given context"""
    flush_object_queue(context, context.oq, context.map)
    wibbrlib.obj.object_queue_clear(context.oq)
    flush_object_queue(context, context.content_oq, context.contmap)
    wibbrlib.obj.object_queue_clear(context.content_oq)


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
    list = wibbrlib.cmp.find_by_kind(components, wibbrlib.cmp.CMP_OBJID)
    id = wibbrlib.cmp.get_string_value(list[0])
    
    list = wibbrlib.cmp.find_by_kind(components, wibbrlib.cmp.CMP_OBJKIND)
    kind = wibbrlib.cmp.get_string_value(list[0])
    (kind, _) = wibbrlib.varint.decode(kind, 0)

    o = wibbrlib.obj.create(id, kind)
    bad = (wibbrlib.cmp.CMP_OBJID, wibbrlib.cmp.CMP_OBJKIND)
    for c in components:
        if wibbrlib.cmp.get_kind(c) not in bad:
            wibbrlib.obj.add(o, c)
    return o


class ObjectCache:

    def __init__(self, context):
        self.MAX = context.config.getint("wibbr", "object-cache-size")
        if self.MAX <= 0:
            self.MAX = context.config.getint("wibbr", "block-size") / 64
            # 64 bytes seems like a reasonably good guess at the typical
            # size of an object that doesn't contain file data. Inodes,
            # for example.
        self.objects = {}
        self.mru = []

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
        self.forget(object_id)
        self.objects[object_id] = object
        self.mru.insert(0, object_id)
        while len(self.mru) > self.MAX:
            self.forget(self.mru[-1])

    def size(self):
        return len(self.mru)

_object_cache = None


def get_object(context, object_id):
    """Fetch an object"""
    global _object_cache
    if _object_cache is None:
        _object_cache = ObjectCache(context)
    o = _object_cache.get(object_id)
    if o:
        return o
        
    block_id = wibbrlib.mapping.get(context.map, object_id)
    if not block_id:
        block_id = wibbrlib.mapping.get(context.contmap, object_id)
    if not block_id:
        return None

    block = get_block(context, block_id)
    if not block:
        raise MissingBlock(block_id, object_id)

    list = wibbrlib.obj.block_decode(block)
    list = wibbrlib.cmp.find_by_kind(list, wibbrlib.cmp.CMP_OBJECT)

    the_one = None
    for component in list:
        subs = wibbrlib.cmp.get_subcomponents(component)
        o = create_object_from_component_list(subs)
        if wibbrlib.obj.get_kind(o) != wibbrlib.obj.OBJ_FILEPART:
            _object_cache.put(o)
        if wibbrlib.obj.get_id(o) == object_id:
            the_one = o
    
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
        return None
    else:
        return wibbrlib.cache.get_block(context.cache, host_id)


def enqueue_object(context, oq, map, object_id, object):
    """Put an object into the object queue, and flush queue if too big"""
    block_size = context.config.getint("wibbr", "block-size")
    cur_size = wibbrlib.obj.object_queue_combined_size(oq)
    if len(object) + cur_size > block_size:
        wibbrlib.io.flush_object_queue(context, oq, map)
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
        enqueue_object(context, context.content_oq, context.contmap, 
                       part_id, o)
        part_ids.append(part_id)
    f.close()

    o = wibbrlib.obj.create(object_id, wibbrlib.obj.OBJ_FILECONTENTS)
    for part_id in part_ids:
        c = wibbrlib.cmp.create(wibbrlib.cmp.CMP_FILEPARTREF, part_id)
        wibbrlib.obj.add(o, c)
    o = wibbrlib.obj.encode(o)
    enqueue_object(context, context.oq, context.map, object_id, o)

    return object_id


class FileContentsObjectMissing(wibbrlib.exception.WibbrException):

    def __init__(self, id):
        self._msg = "Missing file contents object: %s" % id


def get_file_contents(context, fd, cont_id):
    """Write contents of a file in backup to a file descriptor"""
    cont = wibbrlib.io.get_object(context, cont_id)
    if not cont:
        raise FileContentsObjectMissing(cont_id)
    part_ids = wibbrlib.obj.find_strings_by_kind(cont, 
                                              wibbrlib.cmp.CMP_FILEPARTREF)
    for part_id in part_ids:
        part = wibbrlib.io.get_object(context, part_id)
        chunk = wibbrlib.obj.first_string_by_kind(part, 
                                                  wibbrlib.cmp.CMP_FILECHUNK)
        os.write(fd, chunk)


def set_inode(full_pathname, inode):
    subs = wibbrlib.cmp.get_subcomponents(inode)
    mode = wibbrlib.cmp.first_varint_by_kind(subs, wibbrlib.cmp.CMP_ST_MODE)
    atime = wibbrlib.cmp.first_varint_by_kind(subs, wibbrlib.cmp.CMP_ST_ATIME)
    mtime = wibbrlib.cmp.first_varint_by_kind(subs, wibbrlib.cmp.CMP_ST_MTIME)
    os.utime(full_pathname, (atime, mtime))
    os.chmod(full_pathname, stat.S_IMODE(mode))


def _find_refs(components):
    """Return set of all references (recursively) in a list of components"""
    refs = set()
    for c in components:
        kind = wibbrlib.cmp.get_kind(c)
        if wibbrlib.cmp.kind_is_reference(kind):
            refs.add(wibbrlib.cmp.get_string_value(c))
        elif wibbrlib.cmp.kind_is_composite(kind):
            refs = refs.union(_find_refs(wibbrlib.cmp.get_subcomponents(c)))
    return refs


def find_reachable_data_blocks(context, host_block):
    """Find all blocks with data that can be reached from host block"""
    (_, gen_ids, _, _) = wibbrlib.obj.host_block_decode(host_block)
    object_ids = set(gen_ids)
    reachable_block_ids = set()
    while object_ids:
        object_id = object_ids.pop()
        block_id = wibbrlib.mapping.get(context.map, object_id)
        if not block_id:
            block_id = wibbrlib.mapping.get(context.contmap, object_id)
        if block_id not in reachable_block_ids:
            reachable_block_ids.add(block_id)
            block = get_block(context, block_id)
            for ref in _find_refs(wibbrlib.obj.block_decode(block)):
                object_ids.add(ref)
    return [x for x in reachable_block_ids]


def find_map_blocks_in_use(context, host_block, data_block_ids):
    """Given data blocks in use, return map blocks they're mentioned in"""
    data_block_ids = set(data_block_ids)
    (_, _, map_block_ids, contmap_block_ids) = \
        wibbrlib.obj.host_block_decode(host_block)
    used_map_block_ids = set()
    for map_block_id in map_block_ids + contmap_block_ids:
        block = get_block(context, map_block_id)
        list = wibbrlib.obj.block_decode(block)
        list = wibbrlib.cmp.find_by_kind(list, wibbrlib.cmp.CMP_OBJMAP)
        for c in list:
            subs = wibbrlib.cmp.get_subcomponents(c)
            id = wibbrlib.cmp.first_string_by_kind(subs, 
                                        wibbrlib.cmp.CMP_BLOCKREF)
            if id in data_block_ids:
                used_map_block_ids.add(map_block_id)
                break # We already know this entire map block is used
    return [x for x in used_map_block_ids]
    # FIXME: This needs to keep normal and content maps separate.


def collect_garbage(context, host_block):
    """Find files on the server store that are not linked from host object"""
    host_id = context.config.get("wibbr", "host-id")
    data_block_ids = find_reachable_data_blocks(context, host_block)
    map_block_ids = find_map_blocks_in_use(context, host_block, 
                                           data_block_ids)
    files = wibbrlib.backend.list(context.be)
    for id in [host_id] + data_block_ids + map_block_ids:
        if id in files:
            files.remove(id)
    for garbage in files:
        wibbrlib.backend.remove(context.be, garbage)


def load_maps(context, map, block_ids):
    """Load and parse mapping blocks, store results in map"""
    for id in block_ids:
        block = wibbrlib.io.get_block(context, id)
        wibbrlib.mapping.decode_block(map, block)
