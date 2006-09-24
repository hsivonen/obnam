import os
import shutil
import StringIO
import unittest

import wibbr
import wibbrlib.object


class CommandLineParsingTests(unittest.TestCase):

    def config_as_string(self, config):
        f = StringIO.StringIO()
        config.write(f)
        return f.getvalue()

    def testDefaultConfig(self):
        config = wibbr.default_config()
        self.failUnless(config.has_section("wibbr"))
        self.failUnless(config.has_option("wibbr", "block-size"))
        self.failUnless(config.has_option("wibbr", "cache-dir"))
        self.failUnless(config.has_option("wibbr", "local-store"))

    def testEmpty(self):
        config = wibbr.default_config()
        wibbr.parse_args(config, [])
        self.failUnlessEqual(self.config_as_string(config), 
                             self.config_as_string(wibbr.default_config()))

    def testBlockSize(self):
        config = wibbr.default_config()
        wibbr.parse_args(config, ["--block-size=12765"])
        self.failUnlessEqual(config.getint("wibbr", "block-size"), 12765)
        wibbr.parse_args(config, ["--block-size=42"])
        self.failUnlessEqual(config.getint("wibbr", "block-size"), 42)

    def testCacheDir(self):
        config = wibbr.default_config()
        wibbr.parse_args(config, ["--cache-dir=/tmp/foo"])
        self.failUnlessEqual(config.get("wibbr", "cache-dir"), "/tmp/foo")

    def testLocalStore(self):
        config = wibbr.default_config()
        wibbr.parse_args(config, ["--local-store=/tmp/foo"])
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
        oq = wibbrlib.object.object_queue_create()
        block_id = "box"
        object_id = "pink"
        object = "pretty"
        map = wibbrlib.mapping.mapping_create()
        config = wibbr.default_config()
        cache = wibbrlib.cache.init(config)
        be = wibbrlib.backend.init(config, cache)

        self.failUnlessEqual(self.find_block_files(config), [])
        
        (oq, new_block_id) = wibbr.enqueue_object(config, be, map, oq,
                                                  block_id, object_id, object)
        
        self.failUnlessEqual(self.find_block_files(config), [])
        self.failUnlessEqual(block_id, new_block_id)

        shutil.rmtree(config.get("wibbr", "cache-dir"))
