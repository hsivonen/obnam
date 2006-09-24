import ConfigParser
import os
import shutil
import tempfile
import unittest

import backend


class LocalBackendBase(unittest.TestCase):

    def setUp(self):
        self.cachedir = "cachedir"
        self.rootdir = "rootdir"
        
        os.mkdir(self.cachedir)
        os.mkdir(self.rootdir)
        
        config_list = (
            ("wibbr", "block-cache", self.cachedir),
            ("local-backend", "root", self.rootdir)
        )
    
        self.config = ConfigParser.ConfigParser()
        for section, item, value in config_list:
            if not self.config.has_section(section):
                self.config.add_section(section)
            self.config.set(section, item, value)

    def tearDown(self):
        shutil.rmtree(self.cachedir)
        shutil.rmtree(self.rootdir)
        del self.cachedir
        del self.rootdir
        del self.config


class InitTests(LocalBackendBase):

    def testInit(self):
        be = backend.init(self.config)
        self.failUnlessEqual(be.local_root, self.rootdir)


class IdTests(LocalBackendBase):

    def testGenerateBlockId(self):
        be = backend.init(self.config)
        self.failIfEqual(be.curdir, None)
        id = backend.generate_block_id(be)
        self.failUnless(id.startswith(be.curdir))
        id2 = backend.generate_block_id(be)
        self.failIfEqual(id, id2)


class UploadTests(LocalBackendBase):

    def testUpload(self):
        be = backend.init(self.config)
        id = backend.generate_block_id(be)
        block = "pink is pretty"
        ret = backend.upload(be, id, block)
        self.failUnlessEqual(ret, None)
        
        pathname = os.path.join(self.rootdir, id)
        self.failUnless(os.path.isfile(pathname))
        
        f = file(pathname, "r")
        data = f.read()
        f.close()
        self.failUnlessEqual(block, data)


class DownloadTests(LocalBackendBase):

    def testOK(self):
        be = backend.init(self.config)
        id = backend.generate_block_id(be)
        block = "pink is still pretty"
        backend.upload(be, id, block)
        
        success = backend.download(be, id)
        self.failUnlessEqual(success, True)
        
    def testError(self):
        be = backend.init(self.config)
        id = backend.generate_block_id(be)
        success = backend.download(be, id)
        self.failIfEqual(success, True)
