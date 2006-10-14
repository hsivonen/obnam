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
        
        id = wibbr.create_file_contents_object(self.context, filename)

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
        
        id = wibbr.create_file_contents_object(self.context, filename)

        self.failIfEqual(id, None)
        self.failUnlessEqual(wibbrlib.obj.object_queue_ids(self.context.oq),
                                                           [id])

        size = os.path.getsize(filename)
        blocks = size / block_size
        if size % block_size:
            blocks += 1
        self.failUnlessEqual(wibbrlib.mapping.count(self.context.map), blocks)
