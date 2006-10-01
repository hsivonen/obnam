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

    (options, args) = parser.parse_args(argv)
    
    if options.block_size:
        config.set("wibbr", "block-size", "%d" % options.block_size)
    if options.cache_dir:
        config.set("wibbr", "cache-dir", options.cache_dir)
    if options.local_store:
        config.set("wibbr", "local-store", options.local_store)

    return args


def enqueue_object(config, be, map, oq, object_id, object):
    block_size = config.getint("wibbr", "block-size")
    cur_size = wibbrlib.object.object_queue_combined_size(oq)
    if len(object) + cur_size > block_size:
        wibbrlib.backend.flush_object_queue(be, map, oq)
        oq = wibbrlib.object.object_queue_create()
    wibbrlib.object.object_queue_add(oq, object_id, object)
    return oq


def create_file_contents_object(config, be, map, oq, filename):
    object_id = wibbrlib.object.object_id_new()
    block_size = config.getint("wibbr", "block-size")
    f = file(filename, "r")
    while True:
        data = f.read(block_size)
        if not data:
            break
        c = wibbrlib.component.component_encode(
                wibbrlib.component.CMP_FILEDATA, data)
        o = wibbrlib.object.object_encode(object_id, 
                wibbrlib.object.OBJ_FILECONT, [c])
        oq = enqueue_object(config, be, map, oq, object_id, o)
    f.close()
    return object_id, oq
    
    
def backup_single_directory(config, be, amp, oq, pathname, st):
    return None, None


def backup_single_file(config, be, amp, oq, pathname, st):
    return None, None


class UnknownFileType(wibbrlib.exception.WibbrException):

    def __init__(self, pathname, st):
        self._msg = "Unknown file type 0%o for %s" % \
            (stat.ST_ISFMT(st.st_mode), pathname)


def backup_single_item(config, be, map, oq, pathname):
    st = os.stat(pathname)
    
    list = (
        (stat.S_ISDIR, backup_single_directory),
        (stat.S_ISREG, backup_single_file),
    )
    for test, action in list:
        if test(st.st_mode):
            (sig_id, content_id) = action(config, be, map, oq, pathname, st)

            inode_id = wibbrlib.object.object_id_new()
            nst = wibbrlib.object.normalize_stat_result(st)
            inode = wibbrlib.object.inode_object_encode(inode_id, nst,
                                                        sig_id, content_id)
            oq = enqueue_object(config, be, map, oq, inode_id, inode)

            return inode_id, oq

    raise UnknownFileType(pathname, st)


def backup_directory(config, be, map, oq, pairs, dirname):
    (inode_id, oq) = backup_single_item(config, be, map, oq, dirname)
    pairs.append((dirname, inode_id))
    for dirpath, dirnames, filenames in os.walk(dirname):
        for filename in dirnames + filenames:
            pathname = os.path.join(dirpath, filename)
            (inode_id, oq) = backup_single_item(config, be, map, oq, 
                                                pathname)
            pairs.append((pathname, inode_id))
    return oq


def generations(config, cache, be):
    block = wibbrlib.backend.get_host_block(be)
    (_, gen_ids, _) = wibbrlib.object.host_block_decode(block)
    for id in gen_ids:
        print id


def format_perms(perms):
    ru = wu = xu = rg = wg = xg = ro = wo = xo = "-"

    if perms & stat.S_IRUSR:
        ru = "r"
    if perms & stat.S_IWUSR:
        wu = "w"
    if perms & stat.S_IXUSR:
        xu = "x"
    if perms & stat.S_ISUID:
        xu = "s"

    if perms & stat.S_IRGRP:
        rg = "r"
    if perms & stat.S_IWGRP:
        wg = "w"
    if perms & stat.S_IXGRP:
        xg = "x"
    if perms & stat.S_ISGID:
        xg = "s"

    if perms & stat.S_IROTH:
        ro = "r"
    if perms & stat.S_IWOTH:
        wo = "w"
    if perms & stat.S_IXOTH:
        xo = "x"
    if perms & stat.S_ISVTX:
        xo = "t"
    
    return ru + wu + xu + rg + wg + xg + ro + wo + xo


def format_filetype(mode):
    if stat.S_ISDIR(mode):
        return "d"
    elif stat.S_ISREG(mode):
        return "-"
    else:
        return "?"


def format_st_mode(mode):
    (mode, _) = wibbrlib.varint.varint_decode(mode, 0)
    return format_filetype(mode) + format_perms(mode)


def format_integer(data, width):
    (nlink, _) = wibbrlib.varint.varint_decode(data, 0)
    return "%*d" % (width, nlink)


def format_time(data):
    (secs, _) = wibbrlib.varint.varint_decode(data, 0)
    t = time.gmtime(secs)
    return time.strftime("%Y-%m-%d %H:%M:%S", t)


def format_inode(inode):
    fields = (
        (wibbrlib.component.CMP_ST_MODE, format_st_mode),
        (wibbrlib.component.CMP_ST_NLINK, lambda x: format_integer(x, 2)),
        (wibbrlib.component.CMP_ST_UID, lambda x: format_integer(x, 4)),
        (wibbrlib.component.CMP_ST_GID, lambda x: format_integer(x, 4)),
        (wibbrlib.component.CMP_ST_SIZE, lambda x: format_integer(x, 8)),
        (wibbrlib.component.CMP_ST_MTIME, format_time),
    )

    list = []
    for type, func in fields:
        for data in [x[1] for x in inode if x[0] == type]:
            list.append(func(data))
    return " ".join(list)


def show_generations(be, map, gen_ids):
    host_block = wibbrlib.backend.get_host_block(be)
    (host_id, _, map_block_ids) = \
        wibbrlib.object.host_block_decode(host_block)

    for map_block_id in map_block_ids:
        block = wibbrlib.backend.get_block(be, map_block_id)
        wibbrlib.mapping.decode_block(map, block)

    for gen_id in gen_ids:
        print "Generation:", gen_id
        gen = wibbrlib.backend.get_object(be, map, gen_id)
        for type, data in gen:
            if type == wibbrlib.component.CMP_NAMEIPAIR:
                pair = wibbrlib.component.component_decode_all(data, 0)
                (x1, y1) = pair[0]
                (x2, y2) = pair[1]
                if x1 == wibbrlib.component.CMP_INODEREF:
                    (inode_id, filename) = (y1, y2)
                else:
                    (inode_id, filename) = (y2, y1)
                inode = wibbrlib.backend.get_object(be, map, inode_id)
                print "  ", format_inode(inode), filename


class MissingCommandWord(wibbrlib.exception.WibbrException):

    def __init__(self):
        self._msg = "No command word given on command line"


class UnknownCommandWord(wibbrlib.exception.WibbrException):

    def __init__(self, command):
        self._msg = "Unknown command '%s'" % command


def main():
    config = wibbrlib.config.default_config()
    args = parse_options(config, sys.argv[1:])
    cache = wibbrlib.cache.init(config)
    be = wibbrlib.backend.init(config, cache)
    map = wibbrlib.mapping.create()
    oq = wibbrlib.object.object_queue_create()

    if not args:
        raise MissingCommandWord()
        
    command = args[0]
    args = args[1:]
    
    if command == "backup":
        pairs = []
        for name in args:
            if os.path.isdir(name):
                oq = backup_directory(config, be, map, oq, pairs, name)
            else:
                raise Exception("Not a directory: %s" + name)

        gen_id = wibbrlib.object.object_id_new()
        gen = wibbrlib.object.generation_object_encode(gen_id, pairs)
        gen_ids = [gen_id]
        oq = enqueue_object(config, be, map, oq, gen_id, gen)
        if wibbrlib.object.object_queue_combined_size(oq) > 0:
            wibbrlib.backend.flush_object_queue(be, map, oq)

        map_block_id = wibbrlib.backend.generate_block_id(be)
        map_block = wibbrlib.mapping.encode_new_to_block(map, map_block_id)
        wibbrlib.backend.upload(be, map_block_id, map_block)

        host_id = config.get("wibbr", "host-id")
        block = wibbrlib.object.host_block_encode(host_id, gen_ids, 
                    [map_block_id])
        wibbrlib.backend.upload_host_block(be, block)
    elif command == "generations":
        generations(config, cache, be)
    elif command == "show-generations":
        show_generations(be, map, args)
    elif command == "restore":
        pass
    else:
        raise UnknownCommandWord(command)


if __name__ == "__main__":
    main()
