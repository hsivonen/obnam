#!/usr/bin/python

"""Wibbr - a backup program"""


import optparse
import os
import stat
import sys
import time

import wibbrlib


def parse_options(config, argv):
    parser = optparse.OptionParser()
    
    parser.add_option("--block-size",
                      type="int",
                      metavar="SIZE",
                      help="Make blocks that are about SIZE kilobytes")
    
    parser.add_option("--cache-dir",
                      metavar="DIR",
                      help="Store cached blocks in DIR")
    
    parser.add_option("--local-store",
                      metavar="DIR",
                      help="Use DIR for local block storage (not caching)")
    
    parser.add_option("--restore-to", "--to",
                      metavar="DIR",
                      help="Put restored files into DIR")

    (options, args) = parser.parse_args(argv)
    
    if options.block_size:
        config.set("wibbr", "block-size", "%d" % options.block_size)
    if options.cache_dir:
        config.set("wibbr", "cache-dir", options.cache_dir)
    if options.local_store:
        config.set("wibbr", "local-store", options.local_store)
    if options.restore_to:
        config.set("wibbr", "restore-target", options.restore_to)

    return args


def enqueue_object(context, object_id, object):
    block_size = context.config.getint("wibbr", "block-size")
    cur_size = wibbrlib.obj.object_queue_combined_size(context.oq)
    if len(object) + cur_size > block_size:
        wibbrlib.io.flush_object_queue(context)
        wibbrlib.obj.object_queue_clear(context.oq)
    wibbrlib.obj.object_queue_add(context.oq, object_id, object)


def create_file_contents_object(context, filename):
    object_id = wibbrlib.obj.object_id_new()
    part_ids = []
    block_size = context.config.getint("wibbr", "block-size")
    f = file(filename, "r")
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
    
    
def backup_single_directory(context, pathname, st):
    return None, None


def backup_single_file(context, pathname, st):
    id = create_file_contents_object(context, pathname)
    return None, id


class UnknownFileType(wibbrlib.exception.WibbrException):

    def __init__(self, pathname, st):
        self._msg = "Unknown file type 0%o for %s" % \
            (stat.ST_ISFMT(st.st_mode), pathname)


def backup_single_item(context, pathname):
    st = os.stat(pathname)
    
    list = (
        (stat.S_ISDIR, backup_single_directory),
        (stat.S_ISREG, backup_single_file),
    )
    for test, action in list:
        if test(st.st_mode):
            (sig_id, content_id) = action(context, pathname, st)

            inode_id = wibbrlib.obj.object_id_new()
            nst = wibbrlib.obj.normalize_stat_result(st)
            inode = wibbrlib.obj.inode_object_encode(inode_id, nst,
                                                        sig_id, content_id)
            enqueue_object(context, inode_id, inode)

            return inode_id

    raise UnknownFileType(pathname, st)


def backup_directory(context, pairs, dirname):
    inode_id = backup_single_item(context, dirname)
    pairs.append((dirname, inode_id))
    for dirpath, dirnames, filenames in os.walk(dirname):
        for filename in dirnames + filenames:
            pathname = os.path.join(dirpath, filename)
            inode_id = backup_single_item(context, pathname)
            pairs.append((pathname, inode_id))


def generations(context):
    block = wibbrlib.io.get_host_block(context)
    (_, gen_ids, _) = wibbrlib.obj.host_block_decode(block)
    for id in gen_ids:
        print id


def format_st_mode(mode):
    (mode, _) = wibbrlib.varint.decode(mode, 0)
    return wibbrlib.format.filemode(mode)


def format_integer(data, width):
    (nlink, _) = wibbrlib.varint.decode(data, 0)
    return "%*d" % (width, nlink)


def format_time(data):
    (secs, _) = wibbrlib.varint.decode(data, 0)
    t = time.gmtime(secs)
    return time.strftime("%Y-%m-%d %H:%M:%S", t)


def format_inode(inode):
    fields = (
        (wibbrlib.cmp.CMP_ST_MODE, format_st_mode),
        (wibbrlib.cmp.CMP_ST_NLINK, lambda x: format_integer(x, 2)),
        (wibbrlib.cmp.CMP_ST_UID, lambda x: format_integer(x, 4)),
        (wibbrlib.cmp.CMP_ST_GID, lambda x: format_integer(x, 4)),
        (wibbrlib.cmp.CMP_ST_SIZE, lambda x: format_integer(x, 8)),
        (wibbrlib.cmp.CMP_ST_MTIME, format_time),
    )

    list = []
    for type, func in fields:
        for data in [x[1] for x in inode if x[0] == type]:
            list.append(func(data))
    return " ".join(list)


def show_generations(context, gen_ids):
    host_block = wibbrlib.backend.get_host_block(context)
    (host_id, _, map_block_ids) = \
        wibbrlib.obj.host_block_decode(host_block)

    for map_block_id in map_block_ids:
        block = wibbrlib.backend.get_block(context.be, map_block_id)
        wibbrlib.mapping.decode_block(context.map, block)

    for gen_id in gen_ids:
        print "Generation:", gen_id
        gen = wibbrlib.backend.get_object(context.be, context.map, gen_id)
        for c in wibbrlib.obj.get_components(gen):
            type = wibbrlib.cmp.get_type(c)
            if type == wibbrlib.cmp.CMP_NAMEIPAIR:
                pair = wibbrlib.cmp.get_subcomponents(c)
                type2 = wibbrlib.cmp.get_type(pair[0])
                if type2 == wibbrlib.cmp.CMP_INODEREF:
                    inode_id = wibbrlib.cmp.get_string_value(pair[0])
                    filename = wibbrlib.cmp.get_string_value(pair[1])
                else:
                    inode_id = wibbrlib.cmp.get_string_value(pair[1])
                    filename = wibbrlib.cmp.get_string_value(pair[0])
                inode = wibbrlib.backend.get_object(be, map, inode_id)
                print "  ", format_inode(inode), filename


def restore_file_content(context, fd, inode):
    cont_id = wibbrlib.obj.first_string_by_type(inode, 
                                                wibbrlib.cmp.CMP_CONTREF)
    cont = wibbrlib.io.get_object(context, cont_id)
    if not cont:
        return
    list = wibbrlib.obj.get_components(cont)
    part_ids = [wibbrlib.cmp.get_string_value(x) for x in list
                    if wibbrlib.cmp.get_type(x) == 
                            wibbrlib.cmp.CMP_FILEPARTREF]
    for part_id in part_ids:
        part = wibbrlib.io.get_object(context, part_id)
        chunk = wibbrlib.obj.first_string_by_type(part, 
                                                  wibbrlib.cmp.CMP_FILECHUNK)
        os.write(fd, chunk)


def create_filesystem_object(context, full_pathname, inode):
    mode = wibbrlib.obj.first_varint_by_type(inode, wibbrlib.cmp.CMP_ST_MODE)
    if stat.S_ISDIR(mode):
        os.makedirs(full_pathname, 0700)
    elif stat.S_ISREG(mode):
        fd = os.open(full_pathname, os.O_WRONLY | os.O_CREAT, 0)
        restore_file_content(context, fd, inode)
        os.close(fd)


def set_meta_data(full_pathname, inode):
    mode = wibbrlib.obj.first_varint_by_type(inode, wibbrlib.cmp.CMP_ST_MODE)
    atime = wibbrlib.obj.first_varint_by_type(inode, wibbrlib.cmp.CMP_ST_ATIME)
    mtime = wibbrlib.obj.first_varint_by_type(inode, wibbrlib.cmp.CMP_ST_MTIME)
    os.utime(full_pathname, (atime, mtime))
    os.chmod(full_pathname, stat.S_IMODE(mode))


class UnknownGeneration(wibbrlib.exception.WibbrException):

    def __init__(self, gen_id):
        self._msg = "Can't find generation %s" % gen_id


def restore(context, gen_id):
    host_block = wibbrlib.io.get_host_block(context)
    (host_id, _, map_block_ids) = \
        wibbrlib.obj.host_block_decode(host_block)

    for map_block_id in map_block_ids:
        block = wibbrlib.io.get_block(context.be, map_block_id)
        wibbrlib.mapping.decode_block(context.map, block)
    
    gen = wibbrlib.io.get_object(context, gen_id)
    if gen is None:
        raise UnknownGeneration(gen_id)
    
    target = context.config.get("wibbr", "restore-target")
    
    list = []
    for sub in wibbrlib.obj.get_components(gen):
        type = wibbrlib.cmp.get_type(sub)
        if type == wibbrlib.cmp.CMP_NAMEIPAIR:
            parts = wibbrlib.cmp.get_subcomponents(sub)
            type2 = wibbrlib.cmp.get_type(parts[0])
            if type2 == wibbrlib.cmp.CMP_INODEREF:
                inode_id = wibbrlib.cmp.get_string_value(parts[0])
                pathname = wibbrlib.cmp.get_string_value(parts[1])
            else:
                inode_id = wibbrlib.cmp.get_string_value(parts[1])
                pathname = wibbrlib.cmp.get_string_value(parts[0])

            if pathname.startswith(os.sep):
                pathname = "." + pathname
            full_pathname = os.path.join(target, pathname)

            inode = wibbrlib.io.get_object(context, inode_id)
            create_filesystem_object(context, full_pathname, inode)
            list.append((full_pathname, inode))

    list.sort()
    for full_pathname, inode in list:
        set_meta_data(full_pathname, inode)


class MissingCommandWord(wibbrlib.exception.WibbrException):

    def __init__(self):
        self._msg = "No command word given on command line"


class RestoreNeedsGenerationId(wibbrlib.exception.WibbrException):

    def __init__(self):
        self._msg = "The 'restore' operation needs id of generation to restore"


class RestoreOnlyNeedsGenerationId(wibbrlib.exception.WibbrException):

    def __init__(self):
        self._msg = "The 'restore' operation only needs generation id"


class UnknownCommandWord(wibbrlib.exception.WibbrException):

    def __init__(self, command):
        self._msg = "Unknown command '%s'" % command


def main():
    context = wibbrlib.context.create()
    args = parse_options(context.config, sys.argv[1:])
    context.cache = wibbrlib.cache.init(context.config)
    context.be = wibbrlib.backend.init(context.config, context.cache)

    if not args:
        raise MissingCommandWord()
        
    command = args[0]
    args = args[1:]
    
    if command == "backup":
        pairs = []
        for name in args:
            if os.path.isdir(name):
                backup_directory(context, pairs, name)
            else:
                raise Exception("Not a directory: %s" + name)

        gen_id = wibbrlib.obj.object_id_new()
        gen = wibbrlib.obj.generation_object_encode(gen_id, pairs)
        gen_ids = [gen_id]
        enqueue_object(context, gen_id, gen)
        if wibbrlib.obj.object_queue_combined_size(context.oq) > 0:
            wibbrlib.io.flush_object_queue(context)

        map_block_id = wibbrlib.backend.generate_block_id(context.be)
        map_block = wibbrlib.mapping.encode_new_to_block(context.map, 
                                                         map_block_id)
        wibbrlib.backend.upload(context.be, map_block_id, map_block)

        host_id = context.config.get("wibbr", "host-id")
        block = wibbrlib.obj.host_block_encode(host_id, gen_ids, 
                                               [map_block_id])
        wibbrlib.io.upload_host_block(context, block)
    elif command == "generations":
        generations(context)
    elif command == "show-generations":
        show_generations(context, args)
    elif command == "restore":
        if not args:
            raise RestoreNeedsGenerationId()
        elif len(args) > 1:
            raise RestoreOnlyNeedsGenerationId()
        restore(context, args[0])
    else:
        raise UnknownCommandWord(command)


if __name__ == "__main__":
    main()
