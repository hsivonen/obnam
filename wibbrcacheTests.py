import ConfigParser
import os
import shutil
import unittest

import wibbrcache


class CacheBase(unittest.TestCase):

    def setUp(self):
        self.cachedir = "cachedir"
        
        config_list = (
            ("wibbr", "block-cache", self.cachedir),
        )
    
        self.config = ConfigParser.ConfigParser()
        for section, item, value in config_list:
            if not self.config.has_section(section):
                self.config.add_section(section)
            self.config.set(section, item, value)

    def tearDown(self):
        shutil.rmtree(self.cachedir)
        del self.cachedir
        del self.config


class InitTests(CacheBase):

    def testInit(self):
        cache = wibbrcache.init(self.config)
        self.failUnless(os.path.isdir(self.cachedir))
