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


def flush_object_queue(context, oq, map, to_cache):
    """Put all objects in an object queue into a block and upload it
    
    Also put mappings into map. The queue is cleared (emptied) afterwards.
    
    """
    
    if not oq.is_empty():
        block_id = context.be.generate_block_id()
        logging.debug("Creating new object block %s" % block_id)
        block = oq.as_block(block_id)
        context.be.upload_block(block_id, block, to_cache)
        for id in oq.ids():
            obnam.map.add(map, id, block_id)
        oq.clear()


def flush_all_object_queues(context):
    """Flush and clear all object queues in a given context"""
    flush_object_queue(context, context.oq, context.map, True)
    flush_object_queue(context, context.content_oq, context.contmap, False)


def get_block(context, block_id):
    """Get a block from cache or by downloading it"""
    block = context.cache.get_block(block_id)
    if not block:
        block = context.be.download_block(block_id)
    elif context.be.use_gpg():
        logging.debug("Decrypting cached block %s before using it", block_id)
        block = obnam.gpg.decrypt(context.config, block)
    return block


class MissingBlock(obnam.ObnamException):

    def __init__(self, block_id, object_id):
        self._msg = "Block %s for object %s is missing" % \
                        (block_id, object_id)


def create_object_from_component_list(components):
    """Create a new object from a list of components"""
    return obnam.obj.StorageObject(components)


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
        object_id = object.get_id()
        self.forget(object_id)
        self.objects[object_id] = object
        self.mru.insert(0, object_id)
        while len(self.mru) > self.MAX:
            self.forget(self.mru[-1])

    def size(self):
        return len(self.mru)


def get_object(context, object_id):
    """Fetch an object"""
    
    logging.debug("Fetching object %s" % object_id)
    
    if context.object_cache is None:
        context.object_cache = ObjectCache(context)
    o = context.object_cache.get(object_id)
    if o:
        logging.debug("Object is in cache, good")
        return o
        
    logging.debug("Object not in cache, looking up mapping")
    block_id = obnam.map.get(context.map, object_id)
    if not block_id:
        block_id = obnam.map.get(context.contmap, object_id)
    if not block_id:
        return None

    logging.debug("Fetching block")
    block = get_block(context, block_id)

    logging.debug("Decoding block")
    list = obnam.obj.block_decode(block)
    
    logging.debug("Finding objects in block")
    list = obnam.cmp.find_by_kind(list, obnam.cmp.OBJECT)

    logging.debug("Putting objects into object cache")
    the_one = None
    for component in list:
        subs = component.get_subcomponents()
        o = create_object_from_component_list(subs)
        if o.get_kind() != obnam.obj.FILEPART:
            context.object_cache.put(o)
        if o.get_id() == object_id:
            the_one = o

    logging.debug("Returning desired object")    
    return the_one


def upload_host_block(context, host_block):
    """Upload a host block"""
    context.be.upload_block(context.config.get("backup", "host-id"), host_block, False)


def get_host_block(context):
    """Return (and fetch, if needed) the host block, or None if not found"""
    host_id = context.config.get("backup", "host-id")
    logging.debug("Getting host block %s" % host_id)
    try:
        return context.be.download_block(host_id)
    except IOError:
        return None


def enqueue_object(context, oq, map, object_id, object, to_cache):
    """Put an object into the object queue, and flush queue if too big"""
    block_size = context.config.getint("backup", "block-size")
    cur_size = oq.combined_size()
    if len(object) + cur_size > block_size:
        obnam.io.flush_object_queue(context, oq, map, to_cache)
        oq.clear()
    oq.add(object_id, object)


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
        c = obnam.cmp.Component(obnam.cmp.FILECHUNK, data)
        part_id = obnam.obj.object_id_new()
        o = obnam.obj.FilePartObject(id=part_id, components=[c])
        o = o.encode()
        enqueue_object(context, context.content_oq, context.contmap, 
                       part_id, o, False)
        part_ids.append(part_id)

    o = obnam.obj.FileContentsObject(id=object_id)
    for part_id in part_ids:
        c = obnam.cmp.Component(obnam.cmp.FILEPARTREF, part_id)
        o.add(c)
    o = o.encode()
    enqueue_object(context, context.oq, context.map, object_id, o, True)
    if context.progress:
        context.progress.update_current_action(filename)

    return object_id


class FileContentsObjectMissing(obnam.ObnamException):

    def __init__(self, id):
        self._msg = "Missing file contents object: %s" % id


def copy_file_contents(context, fd, cont_id):
    """Write contents of a file in backup to a file descriptor"""
    cont = obnam.io.get_object(context, cont_id)
    if not cont:
        raise FileContentsObjectMissing(cont_id)
    part_ids = cont.find_strings_by_kind(obnam.cmp.FILEPARTREF)
    for part_id in part_ids:
        part = obnam.io.get_object(context, part_id)
        chunk = part.first_string_by_kind(obnam.cmp.FILECHUNK)
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
        prev_delta_id = stack[-1].first_string_by_kind(obnam.cmp.DELTAREF)
        if not prev_delta_id:
            break
        prev_delta = obnam.io.get_object(context, prev_delta_id)
        if not prev_delta:
            logging.error("Can't find DELTA object %s" % prev_delta_id)
            return
        stack.append(prev_delta)

    cont_id = stack[-1].first_string_by_kind(obnam.cmp.CONTREF)
    if not cont_id:
        logging.error("DELTA object chain does not end in CONTREF")
        return
    
    logging.debug("Creating initial version of file")    
    (temp_fd1, temp_name1) = tempfile.mkstemp()
    copy_file_contents(context, temp_fd1, cont_id)
    
    while stack:
        delta = stack[-1]
        stack = stack[:-1]
        logging.debug("Applying DELTA %s" % delta.get_id())
        
        deltapart_ids = delta.find_strings_by_kind(obnam.cmp.DELTAPARTREF)
        
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
    subs = file_component.get_subcomponents()
    stat_component = obnam.cmp.first_by_kind(subs, obnam.cmp.STAT)
    st = obnam.cmp.parse_stat_component(stat_component)
    os.utime(full_pathname, (st.st_atime, st.st_mtime))
    os.chmod(full_pathname, stat.S_IMODE(st.st_mode))


_interesting = set([obnam.cmp.OBJECT, obnam.cmp.FILE])
def _find_refs(components, refs=None):
    """Return set of all references (recursively) in a list of components"""
    if refs is None:
        refs = set()

    for c in components:
        kind = c.get_kind()
        if obnam.cmp.kind_is_reference(kind):
            refs.add(c.get_string_value())
        elif kind in _interesting:
            subs = c.get_subcomponents()
            _find_refs(subs, refs)

    return refs


def find_reachable_data_blocks(context, host_block):
    """Find all blocks with data that can be reached from host block"""
    logging.debug("Finding reachable data")
    (_, gen_ids, _, _) = obnam.obj.host_block_decode(host_block)
    object_ids = set(gen_ids)
    reachable_block_ids = set()
    while object_ids:
        logging.debug("find_reachable_data_blocks: %d remaining" % 
                        len(object_ids))
        object_id = object_ids.pop()
        block_id = obnam.map.get(context.map, object_id)
        if not block_id:
            block_id = obnam.map.get(context.contmap, object_id)
        if not block_id:
            logging.warning("Can't find object %s in any block" % object_id)
        elif block_id not in reachable_block_ids:
            logging.debug("Marking block as reachable: %s" % block_id)
            assert block_id is not None
            reachable_block_ids.add(block_id)
            block = get_block(context, block_id)
            logging.debug("Finding references within block")
            refs = _find_refs(obnam.obj.block_decode(block))
            logging.debug("This block contains %d refs" % len(refs))
            refs = [ref for ref in refs if ref not in reachable_block_ids]
            logging.debug("This block contains %d refs not already reachable"
                            % len(refs))
            for ref in refs:
                object_ids.add(ref)
    return [x for x in reachable_block_ids]


def find_map_blocks_in_use(context, host_block, data_block_ids):
    """Given data blocks in use, return map blocks they're mentioned in"""
    data_block_ids = set(data_block_ids)
    _, _, map_block_ids, contmap_block_ids = obnam.obj.host_block_decode(
                                                host_block)
    used_map_block_ids = set()
    for map_block_id in map_block_ids + contmap_block_ids:
        block = get_block(context, map_block_id)
        list = obnam.obj.block_decode(block)
        assert type(list) == type([])
        list = obnam.cmp.find_by_kind(list, obnam.cmp.OBJMAP)
        for c in list:
            subs = c.get_subcomponents()
            id = obnam.cmp.first_string_by_kind(subs, 
                                        obnam.cmp.BLOCKREF)
            if id in data_block_ids:
                used_map_block_ids.add(map_block_id)
                break # We already know this entire map block is used
    return [x for x in used_map_block_ids]
    # FIXME: This needs to keep normal and content maps separate.


def collect_garbage(context, host_block):
    """Find files on the server store that are not linked from host object"""
    logging.debug("Collecting garbage")
    host_id = context.config.get("backup", "host-id")
    logging.debug("GC: finding reachable data")
    data_block_ids = find_reachable_data_blocks(context, host_block)
    logging.debug("GC: finding map blocks still in use")
    map_block_ids = find_map_blocks_in_use(context, host_block, 
                                           data_block_ids)
    logging.debug("GC: finding all files in store")
    files = context.be.list()
    for id in [host_id] + data_block_ids + map_block_ids:
        if id in files:
            files.remove(id)
    for garbage in files:
        logging.debug("GC: Removing file %s" % garbage)
        context.be.remove(garbage)
    logging.debug("GC: done")


def load_maps(context, map, block_ids):
    """Load and parse mapping blocks, store results in map"""
    num_blocks = len(block_ids)
    logging.debug("Loading %d maps" % num_blocks)
    for i in range(num_blocks):
        id = block_ids[i]
        logging.debug("Loading map block %d/%d: %s" % (i+1, num_blocks, id))
        block = obnam.io.get_block(context, id)
        obnam.map.decode_block(map, block)
