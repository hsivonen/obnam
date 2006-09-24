import ConfigParser
import os
import shutil
import unittest

import wibbrlib.cache


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
        cache = wibbrlib.cache.init(self.config)
        self.failUnless(os.path.isdir(self.cachedir))


class PutTests(CacheBase):

    def testPut(self):
        cache = wibbrlib.cache.init(self.config)
        id = "pink"
        block = "pretty"
        wibbrlib.cache.put_block(cache, id, block)
        
        pathname = os.path.join(self.cachedir, id)
        self.failUnless(os.path.isfile(pathname))
        f = file(pathname, "r")
        self.failUnlessEqual(f.read(), block)
        f.close()


class GetTests(CacheBase):

    def testGet(self):
        cache = wibbrlib.cache.init(self.config)
        id = "pink"
        block = "pretty"
        self.failUnlessEqual(wibbrlib.cache.get_block(cache, id), None)

        wibbrlib.cache.put_block(cache, id, block)
        self.failUnlessEqual(wibbrlib.cache.get_block(cache, id), block)
