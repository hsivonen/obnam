import os
import shutil
import StringIO
import unittest

import wibbr
import wibbrlib.obj


class CommandLineParsingTests(unittest.TestCase):

    def config_as_string(self, config):
        f = StringIO.StringIO()
        config.write(f)
        return f.getvalue()

    def testDefaultConfig(self):
        config = wibbrlib.config.default_config()
        self.failUnless(config.has_section("wibbr"))
        self.failUnless(config.has_option("wibbr", "block-size"))
        self.failUnless(config.has_option("wibbr", "cache-dir"))
        self.failUnless(config.has_option("wibbr", "local-store"))

    def testEmpty(self):
        config = wibbrlib.config.default_config()
        wibbr.parse_options(config, [])
        self.failUnlessEqual(self.config_as_string(config), 
                     self.config_as_string(wibbrlib.config.default_config()))

    def testBlockSize(self):
        config = wibbrlib.config.default_config()
        wibbr.parse_options(config, ["--block-size=12765"])
        self.failUnlessEqual(config.getint("wibbr", "block-size"), 12765)
        wibbr.parse_options(config, ["--block-size=42"])
        self.failUnlessEqual(config.getint("wibbr", "block-size"), 42)

    def testCacheDir(self):
        config = wibbrlib.config.default_config()
        wibbr.parse_options(config, ["--cache-dir=/tmp/foo"])
        self.failUnlessEqual(config.get("wibbr", "cache-dir"), "/tmp/foo")

    def testLocalStore(self):
        config = wibbrlib.config.default_config()
        wibbr.parse_options(config, ["--local-store=/tmp/foo"])
        self.failUnlessEqual(config.get("wibbr", "local-store"), "/tmp/foo")


class ObjectQueuingTests(unittest.TestCase):

    def find_block_files(self, config):
        files = []
        root = config.get("wibbr", "local-store")
        for dirpath, _, filenames in os.walk(root):
            files += [os.path.join(dirpath, x) for x in filenames]
        files.sort()
        return files

    def testEnqueue(self):
        oq = wibbrlib.obj.object_queue_create()
        object_id = "pink"
        object = "pretty"
        map = wibbrlib.mapping.create()
        config = wibbrlib.config.default_config()
        config.set("wibbr", "block-size", "%d" % 128)
        cache = wibbrlib.cache.init(config)
        be = wibbrlib.backend.init(config, cache)

        self.failUnlessEqual(self.find_block_files(config), [])
        
        wibbr.enqueue_object(config, be, map, oq, object_id, object)
        
        self.failUnlessEqual(self.find_block_files(config), [])
        self.failUnlessEqual(wibbrlib.obj.object_queue_combined_size(oq),
                             len(object))
        
        object_id2 = "pink2"
        object2 = "x" * 1024

        wibbr.enqueue_object(config, be, map, oq, object_id2, object2)
        
        self.failUnlessEqual(len(self.find_block_files(config)), 1)
        self.failUnlessEqual(wibbrlib.obj.object_queue_combined_size(oq),
                             len(object2))

        shutil.rmtree(config.get("wibbr", "cache-dir"))
        shutil.rmtree(config.get("wibbr", "local-store"))


class FileContentsTests(unittest.TestCase):

    def setUp(self):
        self.config = wibbrlib.config.default_config()
        self.cache = wibbrlib.cache.init(self.config)
        self.be = wibbrlib.backend.init(self.config, self.cache)

    def tearDown(self):
        for x in ["cache-dir", "local-store"]:
            if os.path.exists(self.config.get("wibbr", x)):
                shutil.rmtree(self.config.get("wibbr", x))

    def testEmptyFile(self):
        map = wibbrlib.mapping.create()
        oq = wibbrlib.obj.object_queue_create()
        filename = "/dev/null"
        
        (id, oq) = wibbr.create_file_contents_object(self.config, self.be, 
                                                     map, oq, filename)

        self.failIfEqual(id, None)
        self.failUnlessEqual(wibbrlib.obj.object_queue_ids(oq), [id])
        self.failUnlessEqual(wibbrlib.mapping.count(map), 0)
            # there's no mapping yet, because the queue is small enough
            # that there has been no need to flush it

    def testNonEmptyFile(self):
        block_size = 16
        self.config.set("wibbr", "block-size", "%d" % block_size)
        map = wibbrlib.mapping.create()
        oq = wibbrlib.obj.object_queue_create()
        filename = "Makefile"
        
        (id, oq) = wibbr.create_file_contents_object(self.config, self.be, 
                                                     map, oq, filename)

        self.failIfEqual(id, None)
        self.failUnlessEqual(wibbrlib.obj.object_queue_ids(oq), [id])

        size = os.path.getsize(filename)
        blocks = size / block_size
        if size % block_size:
            blocks += 1
        self.failUnlessEqual(wibbrlib.mapping.count(map), blocks)
