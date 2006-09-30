"""Wibbr - a backup program"""


import ConfigParser
import optparse
import os
import stat
import sys

import wibbrlib.backend
import wibbrlib.mapping
import wibbrlib.object


def default_config():
    """Return a ConfigParser object with the default builtin configuration"""
    items = (
        ("wibbr", "block-size", "%d" % (64 * 1024)),
        ("wibbr", "cache-dir", "tmp.cachedir"),
        ("wibbr", "local-store", "tmp.local-store"),
    )
    
    config = ConfigParser.RawConfigParser()
    for section, item, value in items:
        if not config.has_section(section):
            config.add_section(section)
        config.set(section, item, value)
    
    return config


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


def flush_object_queue(be, map, oq):
    block_id = wibbrlib.backend.generate_block_id(be)
    block = wibbrlib.object.block_create_from_object_queue(block_id, oq)
    wibbrlib.backend.upload(be, block_id, block)
    for id in wibbrlib.object.object_queue_ids(oq):
        wibbrlib.mapping.mapping_add(map, id, block_id)


def enqueue_object(config, be, map, oq, object_id, object):
    block_size = config.getint("wibbr", "block-size")
    cur_size = wibbrlib.object.object_queue_combined_size(oq)
    if len(object) + cur_size > block_size:
        flush_object_queue(be, map, oq)
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
    print "pathname:", pathname
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


def backup_directory(config, be, map, oq, dirname):
    (inode_id, oq) = backup_single_item(config, be, map, oq, dirname)
    for dirpath, dirnames, filenames in os.walk(dirname):
        for filename in dirnames + filenames:
            pathname = os.path.join(dirpath, filename)
            (inode_id, oq) = backup_single_item(config, be, map, oq, 
                                                pathname)
    return oq


class MissingCommandWord(wibbrlib.exception.WibbrException):

    def __init__(self):
        self._msg = "No command word given on command line"


class UnknownCommandWord(wibbrlib.exception.WibbrException):

    def __init__(self, command):
        self._msg = "Unknown command '%s'" % command


def main():
    config = default_config()
    args = parse_options(config, sys.argv[1:])
    cache = wibbrlib.cache.init(config)
    be = wibbrlib.backend.init(config, cache)
    map = wibbrlib.mapping.mapping_create()
    oq = wibbrlib.object.object_queue_create()

    if not args:
        raise MissingCommandWord()
        
    command = args[0]
    args = args[1:]
    
    if command == "backup":
        for name in args:
            if os.path.isdir(name):
                oq = backup_directory(config, be, map, oq, name)
            else:
                raise Exception("Not a directory: %s" + name)
    elif command == "generations":
        pass
    elif command == "restore":
        pass
    else:
        raise UnknownCommandWord(command)

    if wibbrlib.object.object_queue_combined_size(oq) > 0:
        flush_object_queue(be, map, oq)
 #   write_mappings(map)


if __name__ == "__main__":
    main()
