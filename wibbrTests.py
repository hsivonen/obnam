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

    def testEmpty(self):
        config = wibbr.default_config()
        wibbr.parse_args(config, [])
        self.failUnlessEqual(self.config_as_string(config), 
                             self.config_as_string(wibbr.default_config()))

