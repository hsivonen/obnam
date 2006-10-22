#!/usr/bin/python

"""Wibbr - a backup program"""


import os
import stat
import sys
import time

import wibbrlib


def find_existing_inode(pathname, nst, prevgen_inodes):
    prev = prevgen_inodes.get(pathname, None)
    if prev:
        fields = (
            ("st_dev", wibbrlib.cmp.CMP_ST_DEV),
            ("st_ino", wibbrlib.cmp.CMP_ST_INO),
            ("st_mode", wibbrlib.cmp.CMP_ST_MODE),
            ("st_nlink", wibbrlib.cmp.CMP_ST_NLINK),
            ("st_uid", wibbrlib.cmp.CMP_ST_UID),
            ("st_gid", wibbrlib.cmp.CMP_ST_GID),
            ("st_rdev", wibbrlib.cmp.CMP_ST_RDEV),
            ("st_size", wibbrlib.cmp.CMP_ST_SIZE),
            ("st_blksize", wibbrlib.cmp.CMP_ST_BLKSIZE),
            ("st_blocks", wibbrlib.cmp.CMP_ST_BLOCKS),
            ("st_mtime", wibbrlib.cmp.CMP_ST_MTIME),
            # No atime or ctime, on purpose. They can be changed without
            # requiring a new backup.
        )
        for a, b in fields:
            b_value = wibbrlib.obj.first_varint_by_kind(prev, b)
            if nst[a] != b_value:
                return None
        return prev
    else:
        return None


def backup_single_item(context, pathname, prevgen_inodes):
    st = os.lstat(wibbrlib.io.resolve(context, pathname))
    nst = wibbrlib.obj.normalize_stat_result(st)
    inode = find_existing_inode(pathname, nst, prevgen_inodes)
    if inode:
        return wibbrlib.obj.get_id(inode)

    if stat.S_ISREG(st.st_mode):
        sig_id = None
        cont_id = wibbrlib.io.create_file_contents_object(context, pathname)
    else:
        (sig_id, cont_id) = (None, None)

    inode_id = wibbrlib.obj.object_id_new()
    inode = wibbrlib.obj.inode_object_encode(inode_id, nst, sig_id, cont_id)
    wibbrlib.io.enqueue_object(context, context.oq, inode_id, inode)

    return inode_id


def backup_directory(context, pairs, dirname, prevgen_inodes):
    inode_id = backup_single_item(context, dirname, prevgen_inodes)
    pairs.append((dirname, inode_id))
    dirname = wibbrlib.io.resolve(context, dirname)
    for dirpath, dirnames, filenames in os.walk(dirname):
        dirpath = wibbrlib.io.unsolve(context, dirpath)
        for filename in dirnames + filenames:
            pathname = os.path.join(dirpath, filename)
            inode_id = backup_single_item(context, pathname, prevgen_inodes)
            pairs.append((pathname, inode_id))


def get_files_in_gen(context, gen_id):
    """Return all inodes in a generation, in a dict indexed by filename"""
    gen = wibbrlib.io.get_object(context, gen_id)
    if not gen:
        raise Exception("wtf")
    dict = {}
    for np in wibbrlib.obj.find_by_kind(gen, wibbrlib.cmp.CMP_NAMEIPAIR):
        subs = wibbrlib.cmp.get_subcomponents(np)
        filename = wibbrlib.cmp.first_string_by_kind(subs,
                                     wibbrlib.cmp.CMP_FILENAME)
        inode_id = wibbrlib.cmp.first_string_by_kind(subs,
                                     wibbrlib.cmp.CMP_INODEREF)
        inode = wibbrlib.io.get_object(context, inode_id)
        dict[filename] = inode
    return dict


def backup(context, args):
    host_block = wibbrlib.io.get_host_block(context)
    if host_block:
        (host_id, gen_ids, map_block_ids) = \
            wibbrlib.obj.host_block_decode(host_block)
    
        for map_block_id in map_block_ids:
            block = wibbrlib.io.get_block(context, map_block_id)
            wibbrlib.mapping.decode_block(context.map, block)
    else:
        gen_ids = []
        map_block_ids = []

    if gen_ids:
        prevgen_inodes = get_files_in_gen(context, gen_ids[-1])
    else:
        prevgen_inodes = {}

    pairs = []
    for name in args:
        if name == "/":
            name = "."
        elif name and name[0] == "/":
            name = name[1:]
        if os.path.isdir(wibbrlib.io.resolve(context, name)):
            backup_directory(context, pairs, name, prevgen_inodes)
        else:
            raise Exception("Not a directory: %s" % 
                wibbrlib.io.resolve(context, name))
    
    gen_id = wibbrlib.obj.object_id_new()
    gen = wibbrlib.obj.generation_object_encode(gen_id, pairs)
    gen_ids.append(gen_id)
    wibbrlib.io.enqueue_object(context, context.oq, gen_id, gen)
    wibbrlib.io.flush_all_object_queues(context)

    map_block_id = wibbrlib.backend.generate_block_id(context.be)
    map_block = wibbrlib.mapping.encode_new_to_block(context.map, 
                                                     map_block_id)
    wibbrlib.backend.upload(context.be, map_block_id, map_block)
    map_block_ids.append(map_block_id)

    host_id = context.config.get("wibbr", "host-id")
    block = wibbrlib.obj.host_block_encode(host_id, gen_ids, map_block_ids)
    wibbrlib.io.upload_host_block(context, block)


def generations(context):
    block = wibbrlib.io.get_host_block(context)
    (_, gen_ids, _) = wibbrlib.obj.host_block_decode(block)
    for id in gen_ids:
        print id


def show_generations(context, gen_ids):
    host_block = wibbrlib.io.get_host_block(context)
    (host_id, _, map_block_ids) = \
        wibbrlib.obj.host_block_decode(host_block)

    for map_block_id in map_block_ids:
        block = wibbrlib.io.get_block(context, map_block_id)
        wibbrlib.mapping.decode_block(context.map, block)

    pretty = False
    for gen_id in gen_ids:
        print "Generation:", gen_id
        gen = wibbrlib.io.get_object(context, gen_id)
        list = []
        for c in wibbrlib.obj.find_by_kind(gen, wibbrlib.cmp.CMP_NAMEIPAIR):
            subs = wibbrlib.cmp.get_subcomponents(c)
            inode_id = wibbrlib.cmp.first_string_by_kind(subs, 
                                                 wibbrlib.cmp.CMP_INODEREF)
            filename = wibbrlib.cmp.first_string_by_kind(subs, 
                                                 wibbrlib.cmp.CMP_FILENAME)
            inode = wibbrlib.io.get_object(context, inode_id)
            if pretty:
                list.append((wibbrlib.format.inode_fields(inode), filename))
            else:
                print " ".join(wibbrlib.format.inode_fields(inode)), filename

        if pretty:
            widths = []
            for fields, _ in list:
                for i in range(len(fields)):
                    if i >= len(widths):
                        widths.append(0)
                    widths[i] = max(widths[i], len(fields[i]))
    
            for fields, filename in list:
                cols = []
                for i in range(len(widths)):
                    if i < len(fields):
                        x = fields[i]
                    else:
                        x = ""
                    cols.append("%*s" % (widths[i], x))
                print "  ", " ".join(cols), filename


def create_filesystem_object(context, full_pathname, inode):
    mode = wibbrlib.obj.first_varint_by_kind(inode, wibbrlib.cmp.CMP_ST_MODE)
    if stat.S_ISDIR(mode):
        if not os.path.exists(full_pathname):
            os.makedirs(full_pathname, 0700)
    elif stat.S_ISREG(mode):
        fd = os.open(full_pathname, os.O_WRONLY | os.O_CREAT, 0)
        cont_id = wibbrlib.obj.first_string_by_kind(inode, 
                                                    wibbrlib.cmp.CMP_CONTREF)
        wibbrlib.io.get_file_contents(context, fd, cont_id)
        os.close(fd)


class UnknownGeneration(wibbrlib.exception.WibbrException):

    def __init__(self, gen_id):
        self._msg = "Can't find generation %s" % gen_id


def restore(context, gen_id):
    host_block = wibbrlib.io.get_host_block(context)
    (host_id, _, map_block_ids) = \
        wibbrlib.obj.host_block_decode(host_block)

    for map_block_id in map_block_ids:
        block = wibbrlib.io.get_block(context, map_block_id)
        wibbrlib.mapping.decode_block(context.map, block)
    
    gen = wibbrlib.io.get_object(context, gen_id)
    if gen is None:
        raise UnknownGeneration(gen_id)
    
    target = context.config.get("wibbr", "target-dir")
    
    list = []
    for sub in wibbrlib.obj.find_by_kind(gen, wibbrlib.cmp.CMP_NAMEIPAIR):
        subs = wibbrlib.cmp.get_subcomponents(sub)
        inode_id = wibbrlib.cmp.first_string_by_kind(subs,
                                                 wibbrlib.cmp.CMP_INODEREF)
        pathname = wibbrlib.cmp.first_string_by_kind(subs,
                                                 wibbrlib.cmp.CMP_FILENAME)

        if pathname.startswith(os.sep):
            pathname = "." + pathname
        full_pathname = os.path.join(target, pathname)

        inode = wibbrlib.io.get_object(context, inode_id)
        create_filesystem_object(context, full_pathname, inode)
        list.append((full_pathname, inode))

    list.sort()
    for full_pathname, inode in list:
        wibbrlib.io.set_inode(full_pathname, inode)


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
    args = wibbrlib.config.parse_options(context.config, sys.argv[1:])
    context.cache = wibbrlib.cache.init(context.config)
    context.be = wibbrlib.backend.init(context.config, context.cache)

    if not args:
        raise MissingCommandWord()
        
    command = args[0]
    args = args[1:]
    
    if command == "backup":
        backup(context, args)
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
