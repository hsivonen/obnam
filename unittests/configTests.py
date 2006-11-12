import os
import shutil
import StringIO
import unittest


import obnam


class CommandLineParsingTests(unittest.TestCase):

    def config_as_string(self, config):
        f = StringIO.StringIO()
        config.write(f)
        return f.getvalue()

    def testDefaultConfig(self):
        config = obnam.config.default_config()
        self.failUnless(config.has_section("backup"))
        needed = ["block-size", "cache-dir", "local-store", "target-dir",
                  "host-id", "object-cache-size", "log-level"]
        needed.sort()
        actual = config.options("backup")
        actual.sort()
        self.failUnlessEqual(actual, needed)

    def testEmpty(self):
        config = obnam.config.default_config()
        obnam.config.parse_options(config, [])
        self.failUnlessEqual(self.config_as_string(config), 
                     self.config_as_string(obnam.config.default_config()))

    def testBlockSize(self):
        config = obnam.config.default_config()
        obnam.config.parse_options(config, ["--block-size=12765"])
        self.failUnlessEqual(config.getint("backup", "block-size"), 12765)
        obnam.config.parse_options(config, ["--block-size=42"])
        self.failUnlessEqual(config.getint("backup", "block-size"), 42)

    def testCacheDir(self):
        config = obnam.config.default_config()
        obnam.config.parse_options(config, ["--cache=/tmp/foo"])
        self.failUnlessEqual(config.get("backup", "cache-dir"), "/tmp/foo")

    def testLocalStore(self):
        config = obnam.config.default_config()
        obnam.config.parse_options(config, ["--store=/tmp/foo"])
        self.failUnlessEqual(config.get("backup", "local-store"), "/tmp/foo")

    def testTargetDir(self):
        config = obnam.config.default_config()
        obnam.config.parse_options(config, ["--target=/tmp/foo"])
        self.failUnlessEqual(config.get("backup", "target-dir"), "/tmp/foo")

    def testObjectCacheSize(self):
        config = obnam.config.default_config()
        obnam.config.parse_options(config, ["--object-cache-size=42"])
        self.failUnlessEqual(config.get("backup", "object-cache-size"), "42")
