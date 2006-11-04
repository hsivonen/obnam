#!/usr/bin/python

"""Wibbr - a backup program"""


import logging
import os
import stat
import sys
import time

import wibbrlib


def backup_single_item(context, pathname, new_filelist, prevgen_filelist):
    logging.debug("Backing up %s" % pathname)
    st = os.lstat(wibbrlib.io.resolve(context, pathname))
    nst = wibbrlib.obj.normalize_stat_result(st)
    file_cmp = wibbrlib.filelist.find_matching_inode(prevgen_filelist,
                                                     pathname, st)
    if file_cmp:
        wibbrlib.filelist.add_file_component(new_filelist, pathname, file_cmp)
        return

    logging.debug("Backing up new (version of) file")
    if stat.S_ISREG(st.st_mode):
        sig_id = None
        cont_id = wibbrlib.io.create_file_contents_object(context, pathname)
    else:
        (sig_id, cont_id) = (None, None)

    file_cmp = wibbrlib.filelist.create_file_component_from_stat(pathname,
                                                                 st, cont_id)
    wibbrlib.filelist.add_file_component(new_filelist, pathname, file_cmp)


def backup_directory(context, new_filelist, dirname, prevgen_filelist):
    logging.info("Backing up %s" % dirname)
    backup_single_item(context, dirname, new_filelist, prevgen_filelist)
    dirname = wibbrlib.io.resolve(context, dirname)
    for dirpath, dirnames, filenames in os.walk(dirname):
        dirpath = wibbrlib.io.unsolve(context, dirpath)
        for filename in dirnames + filenames:
            pathname = os.path.join(dirpath, filename)
            backup_single_item(context, pathname, new_filelist, 
                               prevgen_filelist)


def get_filelist_in_gen(context, gen_id):
    """Return the file list in a generation"""
    gen = wibbrlib.io.get_object(context, gen_id)
    if not gen:
        raise Exception("wtf")
    ref = wibbrlib.obj.first_string_by_kind(gen, wibbrlib.cmp.CMP_FILELISTREF)
    if not ref:
        return None
    fl = wibbrlib.io.get_object(context, ref)
    if not fl:
        raise Exception("wtf %s %s" % (ref, repr(fl)))
    return wibbrlib.filelist.from_object(fl)


def backup(context, args):
    logging.info("Starting backup")

    logging.info("Getting and decoding host block")
    host_block = wibbrlib.io.get_host_block(context)
    if host_block:
        (host_id, gen_ids, map_block_ids, contmap_block_ids) = \
            wibbrlib.obj.host_block_decode(host_block)

        logging.info("Decoding mapping blocks")
        wibbrlib.io.load_maps(context, context.map, map_block_ids)
        # FIXME: This needs to deal with contmaps, too.
    else:
        gen_ids = []
        map_block_ids = []
        contmap_block_ids = []

    if gen_ids:
        logging.info("Getting file list for previous generation")
        prevgen_filelist = get_filelist_in_gen(context, gen_ids[-1])
    else:
        prevgen_filelist = None
    if not prevgen_filelist:
        prevgen_filelist = wibbrlib.filelist.create()

    new_filelist = wibbrlib.filelist.create()
    for name in args:
        if name == "/":
            name = "."
        elif name and name[0] == "/":
            name = name[1:]
        if os.path.isdir(wibbrlib.io.resolve(context, name)):
            backup_directory(context, new_filelist, name, prevgen_filelist)
        else:
            raise Exception("Not a directory: %s" % 
                wibbrlib.io.resolve(context, name))

    logging.info("Creating new file list object")    
    filelist_id = wibbrlib.obj.object_id_new()
    filelist_obj = wibbrlib.filelist.to_object(new_filelist, filelist_id)
    filelist_obj = wibbrlib.obj.encode(filelist_obj)
    wibbrlib.io.enqueue_object(context, context.oq, filelist_id, filelist_obj)
    
    logging.info("Creating new generation object")
    gen_id = wibbrlib.obj.object_id_new()
    gen = wibbrlib.obj.generation_object_encode(gen_id, filelist_id)
    gen_ids.append(gen_id)
    wibbrlib.io.enqueue_object(context, context.oq, gen_id, gen)
    wibbrlib.io.flush_all_object_queues(context)

    logging.info("Creating new mapping block")
    map_block_id = wibbrlib.backend.generate_block_id(context.be)
    map_block = wibbrlib.mapping.encode_new_to_block(context.map, 
                                                     map_block_id)
    wibbrlib.backend.upload(context.be, map_block_id, map_block)
    map_block_ids.append(map_block_id)
    # FIXME: This needs to deal with content maps too, in the future.

    logging.info("Creating new host block")
    host_id = context.config.get("wibbr", "host-id")
    block = wibbrlib.obj.host_block_encode(host_id, gen_ids, map_block_ids,
                                           contmap_block_ids)
    wibbrlib.io.upload_host_block(context, block)

    logging.info("Backup done")

def generations(context):
    block = wibbrlib.io.get_host_block(context)
    (_, gen_ids, _, _) = wibbrlib.obj.host_block_decode(block)
    for id in gen_ids:
        print id


def show_generations(context, gen_ids):
    host_block = wibbrlib.io.get_host_block(context)
    (host_id, _, map_block_ids, _) = \
        wibbrlib.obj.host_block_decode(host_block)

    wibbrlib.io.load_maps(context, context.map, map_block_ids)

    pretty = False
    for gen_id in gen_ids:
        print "Generation:", gen_id
        gen = wibbrlib.io.get_object(context, gen_id)
        fl_id = wibbrlib.obj.first_string_by_kind(gen, 
                                wibbrlib.cmp.CMP_FILELISTREF)
        fl = wibbrlib.io.get_object(context, fl_id)
        list = []
        for c in wibbrlib.obj.find_by_kind(fl, wibbrlib.cmp.CMP_FILE):
            subs = wibbrlib.cmp.get_subcomponents(c)
            filename = wibbrlib.cmp.first_string_by_kind(subs, 
                                                 wibbrlib.cmp.CMP_FILENAME)
            if pretty:
                list.append((wibbrlib.format.inode_fields(c), filename))
            else:
                print " ".join(wibbrlib.format.inode_fields(c)), filename

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
    logging.debug("Creating filesystem object %s" % full_pathname)
    subs = wibbrlib.cmp.get_subcomponents(inode)
    mode = wibbrlib.cmp.first_varint_by_kind(subs, wibbrlib.cmp.CMP_ST_MODE)
    if stat.S_ISDIR(mode):
        if not os.path.exists(full_pathname):
            os.makedirs(full_pathname, 0700)
    elif stat.S_ISREG(mode):
        basedir = os.path.dirname(full_pathname)
        if not os.path.exists(basedir):
            os.makedirs(basedir, 0700)
        fd = os.open(full_pathname, os.O_WRONLY | os.O_CREAT, 0)
        cont_id = wibbrlib.cmp.first_string_by_kind(subs, 
                                                    wibbrlib.cmp.CMP_CONTREF)
        wibbrlib.io.get_file_contents(context, fd, cont_id)
        os.close(fd)


class UnknownGeneration(wibbrlib.exception.WibbrException):

    def __init__(self, gen_id):
        self._msg = "Can't find generation %s" % gen_id


def restore(context, gen_id):
    logging.debug("Restoring generation %s" % gen_id)

    logging.debug("Fetching and decoding host block")
    host_block = wibbrlib.io.get_host_block(context)
    (host_id, _, map_block_ids, contmap_block_ids) = \
        wibbrlib.obj.host_block_decode(host_block)

    logging.debug("Decoding mapping blocks")
    wibbrlib.io.load_maps(context, context.map, map_block_ids)
    # FIXME: This needs to deal with content maps too.

    logging.debug("Getting generation object")    
    gen = wibbrlib.io.get_object(context, gen_id)
    if gen is None:
        raise UnknownGeneration(gen_id)
    
    target = context.config.get("wibbr", "target-dir")
    logging.debug("Restoring files under %s" % target)

    logging.debug("Getting list of files in generation")
    fl_id = wibbrlib.obj.first_string_by_kind(gen, 
                        wibbrlib.cmp.CMP_FILELISTREF)
    fl = wibbrlib.io.get_object(context, fl_id)

    logging.debug("Restoring files")
    list = []
    for c in wibbrlib.obj.find_by_kind(fl, wibbrlib.cmp.CMP_FILE):
        subs = wibbrlib.cmp.get_subcomponents(c)
        pathname = wibbrlib.cmp.first_string_by_kind(subs,
                                                 wibbrlib.cmp.CMP_FILENAME)
        logging.debug("Restoring %s" % pathname)

        if pathname.startswith(os.sep):
            pathname = "." + pathname
        full_pathname = os.path.join(target, pathname)

        create_filesystem_object(context, full_pathname, c)
        list.append((full_pathname, c))

    logging.debug("Fixing permissions")
    list.sort()
    for full_pathname, inode in list:
        wibbrlib.io.set_inode(full_pathname, inode)


def forget(context, forgettable_ids):
    host_block = wibbrlib.io.get_host_block(context)
    (host_id, gen_ids, map_block_ids, contmap_block_ids) = \
        wibbrlib.obj.host_block_decode(host_block)

    wibbrlib.io.load_maps(context, context.map, map_block_ids)
    # FIXME: This needs to deal with content maps, too.

    for id in forgettable_ids:
        if id in gen_ids:
            gen_ids.remove(id)
        else:
            print "Warning: Generation", id, "is not known"

    host_id = context.config.get("wibbr", "host-id")
    block = wibbrlib.obj.host_block_encode(host_id, gen_ids, map_block_ids,
                                           contmap_block_ids)
    wibbrlib.io.upload_host_block(context, block)

    wibbrlib.io.collect_garbage(context, block)


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

    wibbrlib.log.setup(context.config)
    logging.info("Wibbr starting up")
        
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
    elif command == "forget":
        forget(context, args)
    else:
        raise UnknownCommandWord(command)

    logging.info("Wibbr finishing")


if __name__ == "__main__":
    main()
