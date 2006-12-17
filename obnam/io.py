# Copyright (C) 2006  Lars Wirzenius <liw@iki.fi>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.


"""Module for doing local file I/O and higher level remote operations"""


import logging
import os
import stat
import subprocess
import tempfile


import obnam


def resolve(context, pathname):
    """Resolve a pathname relative to the user's desired target directory"""
    return os.path.join(context.config.get("backup", "target-dir"), pathname)


def unsolve(context, pathname):
    """Undo resolve(context, pathname)"""
    if pathname == os.sep:
        return pathname
    target = context.config.get("backup", "target-dir")
    if not target.endswith(os.sep):
        target += os.sep
    if pathname.startswith(target):
        return pathname[len(target):]
    else:
        return pathname


def flush_object_queue(context, oq, map):
    """Put all objects in an object queue into a block and upload it
    
    Also put mappings into map. The queue is cleared (emptied) afterwards.
    
    """
    
    if not obnam.obj.queue_is_empty(oq):
        block_id = obnam.backend.generate_block_id(context.be)
        block = obnam.obj.block_create_from_object_queue(block_id, oq)
        obnam.backend.upload(context.be, block_id, block)
        for id in obnam.obj.queue_ids(oq):
            obnam.map.add(map, id, block_id)
        obnam.obj.queue_clear(oq)


def flush_all_object_queues(context):
    """Flush and clear all object queues in a given context"""
    flush_object_queue(context, context.oq, context.map)
    flush_object_queue(context, context.content_oq, context.contmap)


def get_block(context, block_id):
    """Get a block from cache or by downloading it"""
    block = obnam.cache.get_block(context.cache, block_id)
    if not block:
        e = obnam.backend.download(context.be, block_id)
        if e:
            raise e
        block = obnam.cache.get_block(context.cache, block_id)
    return block


class MissingBlock(obnam.exception.ExceptionBase):

    def __init__(self, block_id, object_id):
        self._msg = "Block %s for object %s is missing" % \
                        (block_id, object_id)


def create_object_from_component_list(components):
    """Create a new object from a list of components"""
    list = obnam.cmp.find_by_kind(components, obnam.cmp.OBJID)
    id = obnam.cmp.get_string_value(list[0])
    
    list = obnam.cmp.find_by_kind(components, obnam.cmp.OBJKIND)
    kind = obnam.cmp.get_string_value(list[0])
    (kind, _) = obnam.varint.decode(kind, 0)

    o = obnam.obj.create(id, kind)
    bad = (obnam.cmp.OBJID, obnam.cmp.OBJKIND)
    for c in components:
        if obnam.cmp.get_kind(c) not in bad:
            obnam.obj.add(o, c)
    return o


class ObjectCache:

    def __init__(self, context):
        self.MAX = context.config.getint("backup", "object-cache-size")
        if self.MAX <= 0:
            self.MAX = context.config.getint("backup", "block-size") / 64
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
        object_id = obnam.obj.get_id(object)
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
    
    logging.debug("Fetching object %s" % object_id)
    
    global _object_cache
    if _object_cache is None:
        _object_cache = ObjectCache(context)
    o = _object_cache.get(object_id)
    if o:
        logging.debug("Object is in cache, good")
        return o
        
    logging.debug("Object not in cache, looking up mapping")
    block_id = obnam.map.get(context.map, object_id)
    if not block_id:
        block_id = obnam.map.get(context.contmap, object_id)
    if not block_id:
        logging.warning("No block found that contains object %s" % object_id)
        return None

    logging.debug("Fetching block")
    block = get_block(context, block_id)
    if not block:
        logging.error("Block %s not found in store" % block_id)
        raise MissingBlock(block_id, object_id)

    logging.debug("Decoding block")
    list = obnam.obj.block_decode(block)
    
    logging.debug("Finding objects in block")
    list = obnam.cmp.find_by_kind(list, obnam.cmp.OBJECT)

    logging.debug("Putting objects into object cache")
    the_one = None
    for component in list:
        subs = obnam.cmp.get_subcomponents(component)
        o = create_object_from_component_list(subs)
        if obnam.obj.get_kind(o) != obnam.obj.FILEPART:
            _object_cache.put(o)
        if obnam.obj.get_id(o) == object_id:
            the_one = o

    logging.debug("Returning desired object")    
    return the_one


def upload_host_block(context, host_block):
    """Upload a host block"""
    return obnam.backend.upload(context.be, 
                                   context.config.get("backup", "host-id"), 
                                   host_block)


def get_host_block(context):
    """Return (and fetch, if needed) the host block, or None if not found"""
    host_id = context.config.get("backup", "host-id")
    e = obnam.backend.download(context.be, host_id)
    if e:
        return None
    else:
        return obnam.cache.get_block(context.cache, host_id)


def enqueue_object(context, oq, map, object_id, object):
    """Put an object into the object queue, and flush queue if too big"""
    block_size = context.config.getint("backup", "block-size")
    cur_size = obnam.obj.queue_combined_size(oq)
    if len(object) + cur_size > block_size:
        obnam.io.flush_object_queue(context, oq, map)
        obnam.obj.queue_clear(oq)
    obnam.obj.queue_add(oq, object_id, object)


def create_file_contents_object(context, filename):
    """Create and queue objects to hold a file's contents"""
    object_id = obnam.obj.object_id_new()
    part_ids = []
    odirect_read = context.config.get("backup", "odirect-read")
    block_size = context.config.getint("backup", "block-size")
    f = subprocess.Popen([odirect_read, resolve(context, filename)], 
                         stdout=subprocess.PIPE)
    while True:
        data = f.stdout.read(block_size)
        if not data:
            break
        c = obnam.cmp.create(obnam.cmp.FILECHUNK, data)
        part_id = obnam.obj.object_id_new()
        o = obnam.obj.create(part_id, obnam.obj.FILEPART)
        obnam.obj.add(o, c)
        o = obnam.obj.encode(o)
        enqueue_object(context, context.content_oq, context.contmap, 
                       part_id, o)
        part_ids.append(part_id)

    o = obnam.obj.create(object_id, obnam.obj.FILECONTENTS)
    for part_id in part_ids:
        c = obnam.cmp.create(obnam.cmp.FILEPARTREF, part_id)
        obnam.obj.add(o, c)
    o = obnam.obj.encode(o)
    enqueue_object(context, context.oq, context.map, object_id, o)

    return object_id


class FileContentsObjectMissing(obnam.exception.ExceptionBase):

    def __init__(self, id):
        self._msg = "Missing file contents object: %s" % id


def copy_file_contents(context, fd, cont_id):
    """Write contents of a file in backup to a file descriptor"""
    cont = obnam.io.get_object(context, cont_id)
    if not cont:
        raise FileContentsObjectMissing(cont_id)
    part_ids = obnam.obj.find_strings_by_kind(cont, 
                                              obnam.cmp.FILEPARTREF)
    for part_id in part_ids:
        part = obnam.io.get_object(context, part_id)
        chunk = obnam.obj.first_string_by_kind(part, 
                                                  obnam.cmp.FILECHUNK)
        os.write(fd, chunk)


def reconstruct_file_contents(context, fd, delta_id):
    """Write (to file descriptor) file contents, given an rsync delta"""
    logging.debug("Reconstructing contents %s to %d" % (delta_id, fd))

    logging.debug("Finding chain of DELTAs") 
       
    delta = obnam.io.get_object(context, delta_id)
    if not delta:
        logging.error("Can't find DELTA object to reconstruct: %s" % delta_id)
        return

    stack = [delta]
    while True:
        prev_delta_id = obnam.obj.first_string_by_kind(stack[-1], 
                                                       obnam.cmp.DELTAREF)
        if not prev_delta_id:
            break
        prev_delta = obnam.io.get_object(context, prev_delta_id)
        if not prev_delta:
            logging.error("Can't find DELTA object %s" % prev_delta_id)
            return
        stack.append(prev_delta)

    cont_id = obnam.obj.first_string_by_kind(stack[-1], obnam.cmp.CONTREF)
    if not cont_id:
        logging.error("DELTA object chain does not end in CONTREF")
        return
    
    logging.debug("Creating initial version of file")    
    (temp_fd1, temp_name1) = tempfile.mkstemp()
    copy_file_contents(context, temp_fd1, cont_id)
    
    while stack:
        delta = stack[-1]
        stack = stack[:-1]
        logging.debug("Applying DELTA %s" % obnam.obj.get_id(delta))
        
        deltapart_ids = obnam.obj.find_strings_by_kind(delta, 
                                                       obnam.cmp.DELTAPARTREF)
        
        (temp_fd2, temp_name2) = tempfile.mkstemp()
        obnam.rsync.apply_delta(context, temp_name1, deltapart_ids, 
                                temp_name2)
        os.remove(temp_name1)
        os.close(temp_fd1)
        temp_name1 = temp_name2
        temp_fd1 = temp_fd2

    logging.debug("Copying final version of file to file descriptor %d" % fd)    
    while True:
        data = os.read(temp_fd1, 64 * 1024)
        if not data:
            break
        os.write(fd, data)
    
    os.close(temp_fd1)
    os.remove(temp_name1)


def set_inode(full_pathname, file_component):
    subs = obnam.cmp.get_subcomponents(file_component)
    stat_component = obnam.cmp.first_by_kind(subs, obnam.cmp.STAT)
    st = obnam.cmp.parse_stat_component(stat_component)
    os.utime(full_pathname, (st.st_atime, st.st_mtime))
    os.chmod(full_pathname, stat.S_IMODE(st.st_mode))


def _find_refs(components):
    """Return set of all references (recursively) in a list of components"""
    refs = set()
    for c in components:
        kind = obnam.cmp.get_kind(c)
        if obnam.cmp.kind_is_reference(kind):
            refs.add(obnam.cmp.get_string_value(c))
        elif obnam.cmp.kind_is_composite(kind):
            refs = refs.union(_find_refs(obnam.cmp.get_subcomponents(c)))
    return refs


def find_reachable_data_blocks(context, host_block):
    """Find all blocks with data that can be reached from host block"""
    (_, gen_ids, _, _) = obnam.obj.host_block_decode(host_block)
    object_ids = set(gen_ids)
    reachable_block_ids = set()
    while object_ids:
        object_id = object_ids.pop()
        block_id = obnam.map.get(context.map, object_id)
        if not block_id:
            block_id = obnam.map.get(context.contmap, object_id)
        if block_id not in reachable_block_ids:
            reachable_block_ids.add(block_id)
            block = get_block(context, block_id)
            for ref in _find_refs(obnam.obj.block_decode(block)):
                object_ids.add(ref)
    return [x for x in reachable_block_ids]


def find_map_blocks_in_use(context, host_block, data_block_ids):
    """Given data blocks in use, return map blocks they're mentioned in"""
    data_block_ids = set(data_block_ids)
    (_, _, map_block_ids, contmap_block_ids) = \
        obnam.obj.host_block_decode(host_block)
    used_map_block_ids = set()
    for map_block_id in map_block_ids + contmap_block_ids:
        block = get_block(context, map_block_id)
        list = obnam.obj.block_decode(block)
        list = obnam.cmp.find_by_kind(list, obnam.cmp.OBJMAP)
        for c in list:
            subs = obnam.cmp.get_subcomponents(c)
            id = obnam.cmp.first_string_by_kind(subs, 
                                        obnam.cmp.BLOCKREF)
            if id in data_block_ids:
                used_map_block_ids.add(map_block_id)
                break # We already know this entire map block is used
    return [x for x in used_map_block_ids]
    # FIXME: This needs to keep normal and content maps separate.


def collect_garbage(context, host_block):
    """Find files on the server store that are not linked from host object"""
    host_id = context.config.get("backup", "host-id")
    data_block_ids = find_reachable_data_blocks(context, host_block)
    map_block_ids = find_map_blocks_in_use(context, host_block, 
                                           data_block_ids)
    files = obnam.backend.list(context.be)
    for id in [host_id] + data_block_ids + map_block_ids:
        if id in files:
            files.remove(id)
    for garbage in files:
        obnam.backend.remove(context.be, garbage)


def load_maps(context, map, block_ids):
    """Load and parse mapping blocks, store results in map"""
    for id in block_ids:
        block = obnam.io.get_block(context, id)
        obnam.map.decode_block(map, block)
