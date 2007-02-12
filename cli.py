#!/usr/bin/python2.4
#
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


"""A backup program"""


import logging
import os
import re
import stat
import sys
import time

import obnam


def backup_single_item(context, pathname, new_filelist, prevgen_filelist):
    logging.debug("Seeing if %s needs backing up" % pathname)

    resolved = obnam.io.resolve(context, pathname)
    st = os.lstat(resolved)
    
    file_cmp = obnam.filelist.find_matching_inode(prevgen_filelist,
                                                  pathname, st)
    if file_cmp:
        obnam.filelist.add_file_component(new_filelist, pathname, file_cmp)
        return

    logging.debug("Backing up %s" % pathname)
    sig_id = None
    delta_id = None
    cont_id = None
    if stat.S_ISREG(st.st_mode):
        sigdata = obnam.rsync.compute_signature(context, resolved)
        if sigdata:
            sig_id = obnam.obj.object_id_new()
            sig = obnam.obj.signature_object_encode(sig_id, sigdata)
            obnam.io.enqueue_object(context, context.oq, context.map, 
                                    sig_id, sig)

        prev = obnam.filelist.find(prevgen_filelist, pathname)
        if prev:
            subs = obnam.cmp.get_subcomponents(prev)
            prev_sig_id = obnam.cmp.first_string_by_kind(subs, 
                                                         obnam.cmp.SIGREF)
            if prev_sig_id:
                prev_sig = obnam.io.get_object(context, prev_sig_id)
                if prev_sig:
                    prev_sigdata = obnam.obj.first_string_by_kind(prev_sig,
                                                        obnam.cmp.SIGDATA)
                    if prev_sigdata:
                        xcont_ref = obnam.cmp.first_string_by_kind(subs,
                                                        obnam.cmp.CONTREF)
                        xdelta_ref = obnam.cmp.first_string_by_kind(subs,
                                                        obnam.cmp.DELTAREF)
                    
                        deltapart_ids = obnam.rsync.compute_delta(context,
                                                   prev_sigdata, resolved)

                        delta_id = obnam.obj.object_id_new()
                        delta = obnam.obj.delta_object_encode(delta_id, 
                                                              deltapart_ids,
                                                              xcont_ref,
                                                              xdelta_ref)
                        obnam.io.enqueue_object(context, context.oq, 
                                                context.map, delta_id, delta)

        if not delta_id:
            cont_id = obnam.io.create_file_contents_object(context, pathname)

    file_cmp = obnam.filelist.create_file_component_from_stat(pathname, st,
                                                              cont_id, sig_id,
                                                              delta_id)
    obnam.filelist.add_file_component(new_filelist, pathname, file_cmp)


num_files = 0
def backup_directory(context, new_filelist, dirname, prevgen_filelist):
    patterns = []
    for pattern in context.config.getvalues("backup", "exclude"):
        if pattern:
            logging.debug("Compiling exclusion pattern '%s'" % pattern)
            patterns.append(re.compile(pattern))

    logging.debug("Backing up directory %s" % dirname)
    backup_single_item(context, dirname, new_filelist, prevgen_filelist)
    dirname = obnam.io.resolve(context, dirname)
    for dirpath, dirnames, filenames in os.walk(dirname):
        dirpath = obnam.io.unsolve(context, dirpath)
        for filename in dirnames + filenames:
            pathname = os.path.join(dirpath, filename)
            global num_files
            num_files += 1
            context.progress.update_total_files(num_files)
            context.progress.update_current_file(pathname)
            for pattern in patterns:
                if pattern.search(pathname):
                    logging.debug("Excluding %s" % pathname)
                    break
            else:
                try:
                    backup_single_item(context, pathname, new_filelist, 
                                       prevgen_filelist)
                except EnvironmentError, e:
                    logging.warning("File disappeared or other error: " +
                                    "%s: %s" % (e.filename or "unknown", 
                                    e.strerror or str(e)))
    context.progress.clear()


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

    start_time = int(time.time())
    new_filelist = obnam.filelist.create()
    for name in args:
        if os.path.isdir(obnam.io.resolve(context, name)):
            backup_directory(context, new_filelist, name, prevgen_filelist)
        else:
            raise Exception("Not a directory: %s" % 
                obnam.io.resolve(context, name))
    end_time = int(time.time())

    logging.info("Creating new file list object")    
    filelist_id = obnam.obj.object_id_new()
    filelist_obj = obnam.filelist.to_object(new_filelist, filelist_id)
    filelist_obj = obnam.obj.encode(filelist_obj)
    obnam.io.enqueue_object(context, context.oq, context.map, 
                               filelist_id, filelist_obj)
    
    logging.info("Creating new generation object")
    gen_id = obnam.obj.object_id_new()
    gen = obnam.obj.generation_object_encode(gen_id, filelist_id, start_time,
                                             end_time)
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
    (_, gen_ids, map_block_ids, _) = obnam.obj.host_block_decode(block)
    if context.config.getboolean("backup", "generation-times"):
        obnam.io.load_maps(context, context.map, map_block_ids)
    for id in gen_ids:
        if context.config.getboolean("backup", "generation-times"):
            gen = obnam.io.get_object(context, id)
            if not gen:
                logging.warning("Can't find info about generation %s" % id)
            else:
                start = obnam.obj.first_varint_by_kind(gen, obnam.cmp.GENSTART)
                end = obnam.obj.first_varint_by_kind(gen, obnam.cmp.GENEND)
                print id, obnam.format.timestamp(start), "--", \
                    obnam.format.timestamp(end)
        else:
            print id


def format_period(start, end):
    """Format a period of time in a format that is easy to read for humans"""
    start = time.localtime(start)
    end = time.localtime(end)
    if start[0:3] == end[0:3]:
        return "%s %s - %s" % \
            (time.strftime("%Y-%m-%d", start),
             time.strftime("%H:%M", start),
             time.strftime("%H:%M", end))
    else:
        return "%s %s - %s %s" % \
            (time.strftime("%Y-%m-%d", start),
             time.strftime("%H:%M", start),
             time.strftime("%Y-%m-%d", end),
             time.strftime("%H:%M", end))


def format_generation_period(gen):
    """Return human readable string to show the period of a generation"""
    start_time = obnam.obj.first_varint_by_kind(gen, obnam.cmp.GENSTART)
    end_time = obnam.obj.first_varint_by_kind(gen, obnam.cmp.GENEND)
    return format_period(start_time, end_time)


def show_generations(context, gen_ids):
    host_block = obnam.io.get_host_block(context)
    (host_id, _, map_block_ids, _) = \
        obnam.obj.host_block_decode(host_block)

    obnam.io.load_maps(context, context.map, map_block_ids)

    pretty = False
    for gen_id in gen_ids:
        gen = obnam.io.get_object(context, gen_id)
        start_time = obnam.obj.first_varint_by_kind(gen, obnam.cmp.GENSTART)
        end_time = obnam.obj.first_varint_by_kind(gen, obnam.cmp.GENEND)
        print "Generation: %s %s" % (gen_id, format_generation_period(gen))

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


def hardlink_key(st):
    """Compute key into hardlink lookup table from stat result"""
    return "%d/%d" % (st.st_ino, st.st_dev)


def create_filesystem_object(context, hardlinks, full_pathname, inode):
    logging.debug("Creating filesystem object %s" % full_pathname)
    subs = obnam.cmp.get_subcomponents(inode)
    stat_component = obnam.cmp.first_by_kind(subs, obnam.cmp.STAT)
    st = obnam.cmp.parse_stat_component(stat_component)
    mode = st.st_mode

    if st.st_nlink > 1 and not stat.S_ISDIR(mode):
        key = hardlink_key(st)
        if key in hardlinks:
            existing_link = hardlinks[key]
            os.link(existing_link, full_pathname)
            return
        else:
            hardlinks[key] = full_pathname

    if stat.S_ISDIR(mode):
        if not os.path.exists(full_pathname):
            os.makedirs(full_pathname, 0700)
    elif stat.S_ISREG(mode):
        basedir = os.path.dirname(full_pathname)
        if not os.path.exists(basedir):
            os.makedirs(basedir, 0700)
        fd = os.open(full_pathname, os.O_WRONLY | os.O_CREAT, 0)
        cont_id = obnam.cmp.first_string_by_kind(subs, obnam.cmp.CONTREF)
        if cont_id:
            obnam.io.copy_file_contents(context, fd, cont_id)
        else:
            delta_id = obnam.cmp.first_string_by_kind(subs, 
                                                      obnam.cmp.DELTAREF)
            obnam.io.reconstruct_file_contents(context, fd, delta_id)
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
    hardlinks = {}
    for c in obnam.obj.find_by_kind(fl, obnam.cmp.FILE):
        subs = obnam.cmp.get_subcomponents(c)
        pathname = obnam.cmp.first_string_by_kind(subs,
                                                 obnam.cmp.FILENAME)
        logging.debug("Restoring %s" % pathname)

        if pathname.startswith(os.sep):
            pathname = "." + pathname
        full_pathname = os.path.join(target, pathname)

        create_filesystem_object(context, hardlinks, full_pathname, c)
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
    obnam.backend.set_progress_reporter(context.be, context.progress)

    if not args:
        raise MissingCommandWord()

    obnam.log.setup(context.config)
    logging.info("%s %s starting up" % (obnam.NAME, obnam.VERSION))
        
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

    context.progress.clear()
    logging.info("Store I/O: %d kB read, %d kB written" % 
                 (obnam.backend.get_bytes_read(context.be) / 1024,
                  obnam.backend.get_bytes_written(context.be) / 1024))
    logging.info("Obnam finishing")


if __name__ == "__main__":
    main()
