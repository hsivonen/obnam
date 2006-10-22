import os
import shutil
import StringIO
import unittest


import wibbrlib


class CommandLineParsingTests(unittest.TestCase):

    def config_as_string(self, config):
        f = StringIO.StringIO()
        config.write(f)
        return f.getvalue()

    def testDefaultConfig(self):
        config = wibbrlib.config.default_config()
        self.failUnless(config.has_section("wibbr"))
        needed = ["block-size", "cache-dir", "local-store", "target-dir",
                  "host-id", "object-cache-size"]
        needed.sort()
        actual = config.options("wibbr")
        actual.sort()
        self.failUnlessEqual(actual, needed)

    def testEmpty(self):
        config = wibbrlib.config.default_config()
        wibbrlib.config.parse_options(config, [])
        self.failUnlessEqual(self.config_as_string(config), 
                     self.config_as_string(wibbrlib.config.default_config()))

    def testBlockSize(self):
        config = wibbrlib.config.default_config()
        wibbrlib.config.parse_options(config, ["--block-size=12765"])
        self.failUnlessEqual(config.getint("wibbr", "block-size"), 12765)
        wibbrlib.config.parse_options(config, ["--block-size=42"])
        self.failUnlessEqual(config.getint("wibbr", "block-size"), 42)

    def testCacheDir(self):
        config = wibbrlib.config.default_config()
        wibbrlib.config.parse_options(config, ["--cache=/tmp/foo"])
        self.failUnlessEqual(config.get("wibbr", "cache-dir"), "/tmp/foo")

    def testLocalStore(self):
        config = wibbrlib.config.default_config()
        wibbrlib.config.parse_options(config, ["--store=/tmp/foo"])
        self.failUnlessEqual(config.get("wibbr", "local-store"), "/tmp/foo")

    def testTargetDir(self):
        config = wibbrlib.config.default_config()
        wibbrlib.config.parse_options(config, ["--target=/tmp/foo"])
        self.failUnlessEqual(config.get("wibbr", "target-dir"), "/tmp/foo")

    def testObjectCacheSize(self):
        config = wibbrlib.config.default_config()
        wibbrlib.config.parse_options(config, ["--object-cache-size=42"])
        self.failUnlessEqual(config.get("wibbr", "object-cache-size"), "42")
