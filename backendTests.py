import ConfigParser
import os
import shutil
import tempfile
import unittest

import wibbrlib


class LocalBackendBase(unittest.TestCase):

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


class InitTests(LocalBackendBase):

    def testInit(self):
        be = wibbrlib.backend.init(self.config, self.cache)
        self.failUnlessEqual(be.local_root, self.rootdir)


class IdTests(LocalBackendBase):

    def testGenerateBlockId(self):
        be = wibbrlib.backend.init(self.config, self.cache)
        self.failIfEqual(be.curdir, None)
        id = wibbrlib.backend.generate_block_id(be)
        self.failUnless(id.startswith(be.curdir))
        id2 = wibbrlib.backend.generate_block_id(be)
        self.failIfEqual(id, id2)


class UploadTests(LocalBackendBase):

    def testUpload(self):
        be = wibbrlib.backend.init(self.config, self.cache)
        id = wibbrlib.backend.generate_block_id(be)
        block = "pink is pretty"
        ret = wibbrlib.backend.upload(be, id, block)
        self.failUnlessEqual(ret, None)
        
        pathname = os.path.join(self.rootdir, id)
        self.failUnless(os.path.isfile(pathname))
        
        f = file(pathname, "r")
        data = f.read()
        f.close()
        self.failUnlessEqual(block, data)


class DownloadTests(LocalBackendBase):

    def testOK(self):
        be = wibbrlib.backend.init(self.config, self.cache)
        id = wibbrlib.backend.generate_block_id(be)
        block = "pink is still pretty"
        wibbrlib.backend.upload(be, id, block)
        
        success = wibbrlib.backend.download(be, id)
        self.failUnlessEqual(success, None)
        
    def testError(self):
        be = wibbrlib.backend.init(self.config, self.cache)
        id = wibbrlib.backend.generate_block_id(be)
        success = wibbrlib.backend.download(be, id)
        self.failIfEqual(success, True)


class FileListTests(LocalBackendBase):

    def testFileList(self):
        be = wibbrlib.backend.init(self.config, self.cache)
        self.failUnlessEqual(wibbrlib.backend.list(be), [])
        
        id = "pink"
        block = "pretty"
        wibbrlib.backend.upload(be, id, block)
        list = wibbrlib.backend.list(be)
        filename = os.path.join(self.rootdir, id)
        self.failUnlessEqual(list, [filename])

        f = file(filename, "r")
        block2 = f.read()
        f.close()
        self.failUnlessEqual(block, block2)


class ObjectQueueFlushing(LocalBackendBase):

    def testFlushing(self):
        be = wibbrlib.backend.init(self.config, self.cache)
        map = wibbrlib.mapping.create()
        oq = wibbrlib.object.object_queue_create()
        wibbrlib.object.object_queue_add(oq, "pink", "pretty")
        
        self.failUnlessEqual(wibbrlib.backend.list(be), [])
        
        wibbrlib.backend.flush_object_queue(be, map, oq)

        list = wibbrlib.backend.list(be)
        self.failUnlessEqual(len(list), 1)
        
        b1 = [os.path.basename(x) for x in wibbrlib.mapping.get(map, "pink")]
        b2 = [os.path.basename(x) for x in list]
        self.failUnlessEqual(b1, b2)


class GetObjectTests(LocalBackendBase):

    def upload_object(self, object_id, object):
        oq = wibbrlib.object.object_queue_create()
        wibbrlib.object.object_queue_add(oq, object_id, object)
        wibbrlib.backend.flush_object_queue(self.be, self.map, oq)

    def testGetObject(self):
        self.be = wibbrlib.backend.init(self.config, self.cache)
        self.map = wibbrlib.mapping.create()
        
        id = "pink"
        component = wibbrlib.cmp.create(42, "pretty")
        object = wibbrlib.object.create(id, 0)
        wibbrlib.object.add(object, component)
        object = wibbrlib.object.encode(object)
        self.upload_object(id, object)
        o = wibbrlib.backend.get_object(self.be, self.map, id)

        self.failUnlessEqual(wibbrlib.object.get_id(o), id)
        self.failUnlessEqual(wibbrlib.object.get_type(o), 0)
        list = wibbrlib.object.get_components(o)
        self.failUnlessEqual(len(list), 1)
        self.failUnlessEqual(wibbrlib.cmp.get_type(list[0]), 42)
        self.failUnlessEqual(wibbrlib.cmp.get_string_value(list[0]), 
                             "pretty")


class HostBlock(LocalBackendBase):

    def testFetchHostBlock(self):
        host_id = self.config.get("wibbr", "host-id")
        host = wibbrlib.object.host_block_encode(host_id, ["gen1", "gen2"],
                                                 ["map1", "map2"])
        be = wibbrlib.backend.init(self.config, self.cache)
        
        wibbrlib.backend.upload_host_block(be, host)
        host2 = wibbrlib.backend.get_host_block(be)
        self.failUnlessEqual(host, host2)
