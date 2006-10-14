import os
import shutil
import unittest


import wibbrlib


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
    
        self.config = wibbrlib.config.default_config()
        for section, item, value in config_list:
            if not self.config.has_section(section):
                self.config.add_section(section)
            self.config.set(section, item, value)

        self.cache = wibbrlib.cache.init(self.config)

    def tearDown(self):
        shutil.rmtree(self.cachedir)
        shutil.rmtree(self.rootdir)
        del self.cachedir
        del self.rootdir
        del self.config


class ObjectQueueFlushing(IoBase):

    def testFlushing(self):
        be = wibbrlib.backend.init(self.config, self.cache)
        map = wibbrlib.mapping.create()
        oq = wibbrlib.obj.object_queue_create()
        wibbrlib.obj.object_queue_add(oq, "pink", "pretty")
        
        self.failUnlessEqual(wibbrlib.backend.list(be), [])
        
        wibbrlib.io.flush_object_queue(be, map, oq)

        list = wibbrlib.backend.list(be)
        self.failUnlessEqual(len(list), 1)
        
        b1 = [os.path.basename(x) for x in wibbrlib.mapping.get(map, "pink")]
        b2 = [os.path.basename(x) for x in list]
        self.failUnlessEqual(b1, b2)


class GetObjectTests(IoBase):

    def upload_object(self, object_id, object):
        oq = wibbrlib.obj.object_queue_create()
        wibbrlib.obj.object_queue_add(oq, object_id, object)
        wibbrlib.io.flush_object_queue(self.be, self.map, oq)

    def testGetObject(self):
        self.be = wibbrlib.backend.init(self.config, self.cache)
        self.map = wibbrlib.mapping.create()
        
        id = "pink"
        component = wibbrlib.cmp.create(42, "pretty")
        object = wibbrlib.obj.create(id, 0)
        wibbrlib.obj.add(object, component)
        object = wibbrlib.obj.encode(object)
        self.upload_object(id, object)
        o = wibbrlib.io.get_object(self.be, self.map, id)

        self.failUnlessEqual(wibbrlib.obj.get_id(o), id)
        self.failUnlessEqual(wibbrlib.obj.get_type(o), 0)
        list = wibbrlib.obj.get_components(o)
        self.failUnlessEqual(len(list), 1)
        self.failUnlessEqual(wibbrlib.cmp.get_type(list[0]), 42)
        self.failUnlessEqual(wibbrlib.cmp.get_string_value(list[0]), 
                             "pretty")


class HostBlock(IoBase):

    def testFetchHostBlock(self):
        host_id = self.config.get("wibbr", "host-id")
        host = wibbrlib.obj.host_block_encode(host_id, ["gen1", "gen2"],
                                                 ["map1", "map2"])
        be = wibbrlib.backend.init(self.config, self.cache)
        
        wibbrlib.io.upload_host_block(be, host)
        host2 = wibbrlib.io.get_host_block(be)
        self.failUnlessEqual(host, host2)
