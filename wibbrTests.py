import os
import StringIO
import unittest

import wibbr


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


class RdiffTests(unittest.TestCase):

    def testSignature(self):
        sig = wibbr.compute_signature("Makefile")
        os.system("rdiff signature Makefile Makefile.sig.temp")
        f = file("Makefile.sig.temp")
        data = f.read()
        f.close()
        self.failUnlessEqual(sig, data)
        os.remove("Makefile.sig.temp")

    def testEmptyDelta(self):
        sig = wibbr.compute_signature("Makefile")
        delta = wibbr.compute_delta(sig, "Makefile")
        # The hex string below is what rdiff outputs. I've no idea what
        # the format is, and the empty delta is expressed differently
        # in different situations. Eventually we'll move away from rdiff,
        # and then this should become clearer. --liw, 2006-09-24
        self.failUnlessEqual(delta, "\x72\x73\x02\x36\x45\x00\x5b\x00")
