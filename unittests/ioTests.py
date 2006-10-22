import os
import shutil
import tempfile
import unittest


import wibbrlib


class ResolveTests(unittest.TestCase):

    def test(self):
        context = wibbrlib.context.create()
        # We don't need the fields that are usually initialized manually.

        facit = (
            (".", "/", "/"),
            (".", "/pink", "/pink"),
            (".", "pink", "./pink"),
            ("pink", "/", "/"),
            ("pink", "/pretty", "/pretty"),
            ("pink", "pretty", "pink/pretty"),
            ("/pink", "/", "/"),
            ("/pink", "/pretty", "/pretty"),
            ("/pink", "pretty", "/pink/pretty"),
            ("/", "/", "/"),
        )

        for target, pathname, resolved in facit:
            context.config.set("wibbr", "target-dir", target)
            x = wibbrlib.io.resolve(context, pathname)
            self.failUnlessEqual(x, resolved)
            self.failUnlessEqual(wibbrlib.io.unsolve(context, x), pathname)

        self.failUnlessEqual(wibbrlib.io.unsolve(context, "/pink"), "pink")


class IoBase(unittest.TestCase):

    def setUp(self):
        self.cachedir = "tmp.cachedir"
        self.rootdir = "tmp.rootdir"
        
        os.mkdir(self.cachedir)
        os.mkdir(self.rootdir)
        
        config_list = (
            ("wibbr", "cache-dir", self.cachedir),
            ("wibbr", "local-store", self.rootdir)
        )
    
        self.context = wibbrlib.context.create()
    
        for section, item, value in config_list:
            if not self.context.config.has_section(section):
                self.context.config.add_section(section)
            self.context.config.set(section, item, value)

        self.context.cache = wibbrlib.cache.init(self.context.config)
        self.context.be = wibbrlib.backend.init(self.context.config, 
                                                self.context.cache)

    def tearDown(self):
        shutil.rmtree(self.cachedir)
        shutil.rmtree(self.rootdir)
        del self.cachedir
        del self.rootdir
        del self.context


class ObjectQueueFlushing(IoBase):

    def testEmptyQueue(self):
        wibbrlib.io.flush_object_queue(self.context, self.context.oq)
        list = wibbrlib.backend.list(self.context.be)
        self.failUnlessEqual(list, [])

    def testFlushing(self):
        wibbrlib.obj.object_queue_add(self.context.oq, "pink", "pretty")
        
        self.failUnlessEqual(wibbrlib.backend.list(self.context.be), [])
        
        wibbrlib.io.flush_object_queue(self.context, self.context.oq)

        list = wibbrlib.backend.list(self.context.be)
        self.failUnlessEqual(len(list), 1)
        
        b1 = os.path.basename(wibbrlib.mapping.get(self.context.map, "pink"))
        b2 = os.path.basename(list[0])
        self.failUnlessEqual(b1, b2)

    def testFlushAll(self):
        wibbrlib.obj.object_queue_add(self.context.oq, "pink", "pretty")
        wibbrlib.obj.object_queue_add(self.context.content_oq, "x", "y")
        wibbrlib.io.flush_all_object_queues(self.context)
        self.failUnlessEqual(len(wibbrlib.backend.list(self.context.be)), 2)
        self.failUnlessEqual(
          wibbrlib.obj.object_queue_combined_size(self.context.oq), 0)
        self.failUnlessEqual(
          wibbrlib.obj.object_queue_combined_size(self.context.content_oq), 0)


class GetObjectTests(IoBase):

    def upload_object(self, object_id, object):
        wibbrlib.obj.object_queue_add(self.context.oq, object_id, object)
        wibbrlib.io.flush_object_queue(self.context, self.context.oq)

    def testGetObject(self):
        id = "pink"
        component = wibbrlib.cmp.create(42, "pretty")
        object = wibbrlib.obj.create(id, 0)
        wibbrlib.obj.add(object, component)
        object = wibbrlib.obj.encode(object)
        self.upload_object(id, object)
        o = wibbrlib.io.get_object(self.context, id)

        self.failUnlessEqual(wibbrlib.obj.get_id(o), id)
        self.failUnlessEqual(wibbrlib.obj.get_kind(o), 0)
        list = wibbrlib.obj.get_components(o)
        self.failUnlessEqual(len(list), 1)
        self.failUnlessEqual(wibbrlib.cmp.get_kind(list[0]), 42)
        self.failUnlessEqual(wibbrlib.cmp.get_string_value(list[0]), 
                             "pretty")


class HostBlock(IoBase):

    def testFetchHostBlock(self):
        host_id = self.context.config.get("wibbr", "host-id")
        host = wibbrlib.obj.host_block_encode(host_id, ["gen1", "gen2"],
                                                 ["map1", "map2"])
        be = wibbrlib.backend.init(self.context.config, self.context.cache)
        
        wibbrlib.io.upload_host_block(self.context, host)
        host2 = wibbrlib.io.get_host_block(self.context)
        self.failUnlessEqual(host, host2)


class ObjectQueuingTests(unittest.TestCase):

    def find_block_files(self, config):
        files = []
        root = config.get("wibbr", "local-store")
        for dirpath, _, filenames in os.walk(root):
            files += [os.path.join(dirpath, x) for x in filenames]
        files.sort()
        return files

    def testEnqueue(self):
        context = wibbrlib.context.create()
        object_id = "pink"
        object = "pretty"
        context.config.set("wibbr", "block-size", "%d" % 128)
        context.cache = wibbrlib.cache.init(context.config)
        context.be = wibbrlib.backend.init(context.config, context.cache)

        self.failUnlessEqual(self.find_block_files(context.config), [])
        
        wibbrlib.io.enqueue_object(context, context.oq, object_id, object)
        
        self.failUnlessEqual(self.find_block_files(context.config), [])
        self.failUnlessEqual(
            wibbrlib.obj.object_queue_combined_size(context.oq),
            len(object))
        
        object_id2 = "pink2"
        object2 = "x" * 1024

        wibbrlib.io.enqueue_object(context, context.oq, object_id2, object2)
        
        self.failUnlessEqual(len(self.find_block_files(context.config)), 1)
        self.failUnlessEqual(
            wibbrlib.obj.object_queue_combined_size(context.oq),
            len(object2))

        shutil.rmtree(context.config.get("wibbr", "cache-dir"))
        shutil.rmtree(context.config.get("wibbr", "local-store"))


class FileContentsTests(unittest.TestCase):

    def setUp(self):
        self.context = wibbrlib.context.create()
        self.context.cache = wibbrlib.cache.init(self.context.config)
        self.context.be = wibbrlib.backend.init(self.context.config, 
                                                self.context.cache)

    def tearDown(self):
        for x in ["cache-dir", "local-store"]:
            if os.path.exists(self.context.config.get("wibbr", x)):
                shutil.rmtree(self.context.config.get("wibbr", x))

    def testEmptyFile(self):
        filename = "/dev/null"
        
        id = wibbrlib.io.create_file_contents_object(self.context, filename)

        self.failIfEqual(id, None)
        self.failUnlessEqual(wibbrlib.obj.object_queue_ids(self.context.oq), 
                             [id])
        self.failUnlessEqual(wibbrlib.mapping.count(self.context.map), 0)
            # there's no mapping yet, because the queue is small enough
            # that there has been no need to flush it

    def testNonEmptyFile(self):
        block_size = 16
        self.context.config.set("wibbr", "block-size", "%d" % block_size)
        filename = "Makefile"
        
        id = wibbrlib.io.create_file_contents_object(self.context, filename)

        self.failIfEqual(id, None)
        self.failUnlessEqual(wibbrlib.obj.object_queue_ids(self.context.oq),
                                                           [id])

    def testRestore(self):
        block_size = 16
        self.context.config.set("wibbr", "block-size", "%d" % block_size)
        filename = "Makefile"
        
        id = wibbrlib.io.create_file_contents_object(self.context, filename)
        wibbrlib.io.flush_object_queue(self.context, self.context.oq)
        wibbrlib.io.flush_object_queue(self.context, self.context.content_oq)
        
        (fd, name) = tempfile.mkstemp()
        wibbrlib.io.get_file_contents(self.context, fd, id)
        os.close(fd)
        
        f = file(name, "r")
        data1 = f.read()
        f.close()
        os.remove(name)
        
        f = file(filename, "r")
        data2 = f.read()
        f.close()
        
        self.failUnlessEqual(data1, data2)


class MetaDataTests(unittest.TestCase):

    def testSet(self):
        o = wibbrlib.obj.create("pink", wibbrlib.obj.OBJ_INODE)
        fields = (
            (wibbrlib.cmp.CMP_ST_MODE, 0100664),
            (wibbrlib.cmp.CMP_ST_ATIME, 12765),
            (wibbrlib.cmp.CMP_ST_MTIME, 42),
        )
        for kind, value in fields:
            c = wibbrlib.cmp.create(kind, wibbrlib.varint.encode(value))
            wibbrlib.obj.add(o, c)

        (fd, name) = tempfile.mkstemp()
        os.close(fd)
        
        os.chmod(name, 0)
        
        wibbrlib.io.set_inode(name, o)
        
        st = os.stat(name)
        
        self.failUnlessEqual(st.st_mode, fields[0][1])
        self.failUnlessEqual(st.st_atime, fields[1][1])
        self.failUnlessEqual(st.st_mtime, fields[2][1])


class ObjectCacheTests(unittest.TestCase):

    def setUp(self):
        self.object = wibbrlib.obj.create("pink", 1)
        self.object2 = wibbrlib.obj.create("pretty", 1)
        self.object3 = wibbrlib.obj.create("beautiful", 1)

    def testCreate(self):
        context = wibbrlib.context.create()
        oc = wibbrlib.io.ObjectCache(context)
        self.failUnlessEqual(oc.size(), 0)
        self.failUnless(oc.MAX > 0)
        
    def testPut(self):
        context = wibbrlib.context.create()
        oc = wibbrlib.io.ObjectCache(context)
        self.failUnlessEqual(oc.get("pink"), None)
        oc.put(self.object)
        self.failUnlessEqual(oc.get("pink"), self.object)

    def testPutWithOverflow(self):
        context = wibbrlib.context.create()
        oc = wibbrlib.io.ObjectCache(context)
        oc.MAX = 1
        oc.put(self.object)
        self.failUnlessEqual(oc.size(), 1)
        self.failUnlessEqual(oc.get("pink"), self.object)
        oc.put(self.object2)
        self.failUnlessEqual(oc.size(), 1)
        self.failUnlessEqual(oc.get("pink"), None)
        self.failUnlessEqual(oc.get("pretty"), self.object2)

    def testPutWithOverflowPart2(self):
        context = wibbrlib.context.create()
        oc = wibbrlib.io.ObjectCache(context)
        oc.MAX = 2

        oc.put(self.object)
        oc.put(self.object2)
        self.failUnlessEqual(oc.size(), 2)
        self.failUnlessEqual(oc.get("pink"), self.object)
        self.failUnlessEqual(oc.get("pretty"), self.object2)

        oc.get("pink")
        oc.put(self.object3)
        self.failUnlessEqual(oc.size(), 2)
        self.failUnlessEqual(oc.get("pink"), self.object)
        self.failUnlessEqual(oc.get("pretty"), None)
        self.failUnlessEqual(oc.get("beautiful"), self.object3)


class GarbageCollectionTests(IoBase):

    def testFindUnreachableFiles(self):
        host_id = self.context.config.get("wibbr", "host-id")
        host = wibbrlib.obj.host_block_encode(host_id, [], [])
        wibbrlib.io.upload_host_block(self.context, host)

        block_id = wibbrlib.backend.generate_block_id(self.context.be)
        wibbrlib.backend.upload(self.context.be, block_id, "pink")

        files = wibbrlib.backend.list(self.context.be)
        self.failUnlessEqual(files, [host_id, block_id])

        wibbrlib.io.collect_garbage(self.context)
        files = wibbrlib.backend.list(self.context.be)
        self.failUnlessEqual(files, [host_id])
