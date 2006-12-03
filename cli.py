#!/usr/bin/python2.4

"""A backup program"""


NAME = "obnam"
VERSION = "0.2"


import logging
import os
import stat
import sys
import time

import obnam


def backup_single_item(context, pathname, new_filelist, prevgen_filelist):
    logging.debug("Seeing if %s needs backing up" % pathname)
    resolved = obnam.io.resolve(context, pathname)
    st = os.lstat(resolved)
    nst = obnam.obj.normalize_stat_result(st)
    file_cmp = obnam.filelist.find_matching_inode(prevgen_filelist,
                                                  pathname, st)
    if file_cmp:
        obnam.filelist.add_file_component(new_filelist, pathname, file_cmp)
        return

    logging.info("Backing up %s" % pathname)
    if stat.S_ISREG(st.st_mode):
        sigdata = obnam.rsync.compute_signature(resolved)
        if sigdata:
            sig_id = obnam.obj.object_id_new()
            sig = obnam.obj.signature_object_encode(sig_id, sigdata)
            obnam.io.enqueue_object(context, context.oq, context.map, 
                                    sig_id, sig)
        else:
            sig_id = None
        cont_id = obnam.io.create_file_contents_object(context, pathname)
    else:
        (sig_id, cont_id) = (None, None)

    file_cmp = obnam.filelist.create_file_component_from_stat(pathname, st,
                                                              cont_id, sig_id)
    obnam.filelist.add_file_component(new_filelist, pathname, file_cmp)


def backup_directory(context, new_filelist, dirname, prevgen_filelist):
    logging.info("Backing up %s" % dirname)
    backup_single_item(context, dirname, new_filelist, prevgen_filelist)
    dirname = obnam.io.resolve(context, dirname)
    for dirpath, dirnames, filenames in os.walk(dirname):
        dirpath = obnam.io.unsolve(context, dirpath)
        for filename in dirnames + filenames:
            pathname = os.path.join(dirpath, filename)
            backup_single_item(context, pathname, new_filelist, 
                               prevgen_filelist)


def get_filelist_in_gen(context, gen_id):
    """Return the file list in a generation"""
    logging.debug("Getting list of files in generation %s" % gen_id)
    gen = obnam.io.get_object(context, gen_id)
    if not gen:
        raise Exception("wtf")
    logging.debug("Finding first FILELISTREF component in generation")
    ref = obnam.obj.first_string_by_kind(gen, obnam.cmp.FILELISTREF)
    if not ref:
        logging.debug("No FILELISTREFs")
        return None
    logging.debug("Getting file list object")
    fl = obnam.io.get_object(context, ref)
    if not fl:
        raise Exception("wtf %s %s" % (ref, repr(fl)))
    logging.debug("Creating filelist object from components")
    ret = obnam.filelist.from_object(fl)
    logging.debug("Got file list")
    return ret


def backup(context, args):
    logging.info("Starting backup")

    logging.info("Getting and decoding host block")
    host_block = obnam.io.get_host_block(context)
    if host_block:
        (host_id, gen_ids, map_block_ids, contmap_block_ids) = \
            obnam.obj.host_block_decode(host_block)

        logging.info("Decoding mapping blocks")
        obnam.io.load_maps(context, context.map, map_block_ids)
        # We don't need to load in file data, therefore we don't load
        # the content map blocks.
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
        prevgen_filelist = obnam.filelist.create()

    new_filelist = obnam.filelist.create()
    for name in args:
        if name == "/":
            name = "."
        elif name and name[0] == "/":
            name = name[1:]
        if os.path.isdir(obnam.io.resolve(context, name)):
            backup_directory(context, new_filelist, name, prevgen_filelist)
        else:
            raise Exception("Not a directory: %s" % 
                obnam.io.resolve(context, name))

    logging.info("Creating new file list object")    
    filelist_id = obnam.obj.object_id_new()
    filelist_obj = obnam.filelist.to_object(new_filelist, filelist_id)
    filelist_obj = obnam.obj.encode(filelist_obj)
    obnam.io.enqueue_object(context, context.oq, context.map, 
                               filelist_id, filelist_obj)
    
    logging.info("Creating new generation object")
    gen_id = obnam.obj.object_id_new()
    gen = obnam.obj.generation_object_encode(gen_id, filelist_id)
    gen_ids.append(gen_id)
    obnam.io.enqueue_object(context, context.oq, context.map, gen_id, gen)
    obnam.io.flush_all_object_queues(context)

    logging.info("Creating new mapping blocks")
    if obnam.map.get_new(context.map):
        map_block_id = obnam.backend.generate_block_id(context.be)
        map_block = obnam.map.encode_new_to_block(context.map, 
                                                         map_block_id)
        obnam.backend.upload(context.be, map_block_id, map_block)
        map_block_ids.append(map_block_id)

    if obnam.map.get_new(context.contmap):
        contmap_block_id = obnam.backend.generate_block_id(context.be)
        contmap_block = obnam.map.encode_new_to_block(context.contmap, 
                                                             contmap_block_id)
        obnam.backend.upload(context.be, contmap_block_id, contmap_block)
        contmap_block_ids.append(contmap_block_id)

    logging.info("Creating new host block")
    host_id = context.config.get("backup", "host-id")
    block = obnam.obj.host_block_encode(host_id, gen_ids, map_block_ids,
                                           contmap_block_ids)
    obnam.io.upload_host_block(context, block)

    logging.info("Backup done")

def generations(context):
    block = obnam.io.get_host_block(context)
    (_, gen_ids, _, _) = obnam.obj.host_block_decode(block)
    for id in gen_ids:
        print id


def show_generations(context, gen_ids):
    host_block = obnam.io.get_host_block(context)
    (host_id, _, map_block_ids, _) = \
        obnam.obj.host_block_decode(host_block)

    obnam.io.load_maps(context, context.map, map_block_ids)

    pretty = False
    for gen_id in gen_ids:
        print "Generation:", gen_id
        gen = obnam.io.get_object(context, gen_id)
        fl_id = obnam.obj.first_string_by_kind(gen, 
                                obnam.cmp.FILELISTREF)
        fl = obnam.io.get_object(context, fl_id)
        list = []
        for c in obnam.obj.find_by_kind(fl, obnam.cmp.FILE):
            subs = obnam.cmp.get_subcomponents(c)
            filename = obnam.cmp.first_string_by_kind(subs, 
                                                 obnam.cmp.FILENAME)
            if pretty:
                list.append((obnam.format.inode_fields(c), filename))
            else:
                print " ".join(obnam.format.inode_fields(c)), filename

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
    subs = obnam.cmp.get_subcomponents(inode)
    mode = obnam.cmp.first_varint_by_kind(subs, obnam.cmp.ST_MODE)
    if stat.S_ISDIR(mode):
        if not os.path.exists(full_pathname):
            os.makedirs(full_pathname, 0700)
    elif stat.S_ISREG(mode):
        basedir = os.path.dirname(full_pathname)
        if not os.path.exists(basedir):
            os.makedirs(basedir, 0700)
        fd = os.open(full_pathname, os.O_WRONLY | os.O_CREAT, 0)
        cont_id = obnam.cmp.first_string_by_kind(subs, 
                                                    obnam.cmp.CONTREF)
        obnam.io.copy_file_contents(context, fd, cont_id)
        os.close(fd)


class UnknownGeneration(obnam.exception.ExceptionBase):

    def __init__(self, gen_id):
        self._msg = "Can't find generation %s" % gen_id


def restore(context, gen_id):
    logging.debug("Restoring generation %s" % gen_id)

    logging.debug("Fetching and decoding host block")
    host_block = obnam.io.get_host_block(context)
    (host_id, _, map_block_ids, contmap_block_ids) = \
        obnam.obj.host_block_decode(host_block)

    logging.debug("Decoding mapping blocks")
    obnam.io.load_maps(context, context.map, map_block_ids)
    obnam.io.load_maps(context, context.contmap, contmap_block_ids)

    logging.debug("Getting generation object")    
    gen = obnam.io.get_object(context, gen_id)
    if gen is None:
        raise UnknownGeneration(gen_id)
    
    target = context.config.get("backup", "target-dir")
    logging.debug("Restoring files under %s" % target)

    logging.debug("Getting list of files in generation")
    fl_id = obnam.obj.first_string_by_kind(gen, 
                        obnam.cmp.FILELISTREF)
    fl = obnam.io.get_object(context, fl_id)

    logging.debug("Restoring files")
    list = []
    for c in obnam.obj.find_by_kind(fl, obnam.cmp.FILE):
        subs = obnam.cmp.get_subcomponents(c)
        pathname = obnam.cmp.first_string_by_kind(subs,
                                                 obnam.cmp.FILENAME)
        logging.debug("Restoring %s" % pathname)

        if pathname.startswith(os.sep):
            pathname = "." + pathname
        full_pathname = os.path.join(target, pathname)

        create_filesystem_object(context, full_pathname, c)
        list.append((full_pathname, c))

    logging.debug("Fixing permissions")
    list.sort()
    for full_pathname, inode in list:
        obnam.io.set_inode(full_pathname, inode)


def forget(context, forgettable_ids):
    host_block = obnam.io.get_host_block(context)
    (host_id, gen_ids, map_block_ids, contmap_block_ids) = \
        obnam.obj.host_block_decode(host_block)

    obnam.io.load_maps(context, context.map, map_block_ids)
    obnam.io.load_maps(context, context.contmap, contmap_block_ids)

    for id in forgettable_ids:
        if id in gen_ids:
            gen_ids.remove(id)
        else:
            print "Warning: Generation", id, "is not known"

    host_id = context.config.get("backup", "host-id")
    block = obnam.obj.host_block_encode(host_id, gen_ids, map_block_ids,
                                           contmap_block_ids)
    obnam.io.upload_host_block(context, block)

    obnam.io.collect_garbage(context, block)


def version():
    """Report program name and version number of program to user"""
    print "%s version %s" % (NAME, VERSION)


class MissingCommandWord(obnam.exception.ExceptionBase):

    def __init__(self):
        self._msg = "No command word given on command line"


class RestoreNeedsGenerationId(obnam.exception.ExceptionBase):

    def __init__(self):
        self._msg = "The 'restore' operation needs id of generation to restore"


class RestoreOnlyNeedsGenerationId(obnam.exception.ExceptionBase):

    def __init__(self):
        self._msg = "The 'restore' operation only needs generation id"


class UnknownCommandWord(obnam.exception.ExceptionBase):

    def __init__(self, command):
        self._msg = "Unknown command '%s'" % command


def main():
    context = obnam.context.create()
    args = obnam.config.parse_options(context.config, sys.argv[1:])
    context.cache = obnam.cache.init(context.config)
    context.be = obnam.backend.init(context.config, context.cache)

    if not args:
        raise MissingCommandWord()

    obnam.log.setup(context.config)
    logging.info("%s %s starting up" % (NAME, VERSION))
        
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
    elif command == "version":
        version()
    else:
        raise UnknownCommandWord(command)

    logging.info("Obnam finishing")


if __name__ == "__main__":
    main()
