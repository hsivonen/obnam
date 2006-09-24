import ConfigParser
import shutil
import tempfile
import unittest

import backend


class LocalBackendBase(unittest.TestCase):

    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        self.config = ConfigParser.ConfigParser()
        self.config.add_section("local-backend")
        self.config.set("local-backend", "root", self.tempdir)

    def tearDown(self):
        shutil.rmtree(self.tempdir)
        del self.tempdir
        del self.config


class InitTests(LocalBackendBase):

    def testInit(self):
        be = backend.init(self.config)
        self.failUnlessEqual(be.local_root, self.tempdir)


class IdTests(LocalBackendBase):

    def testGenerateBlockId(self):
        be = backend.init(self.config)
        self.failIfEqual(be.curdir, None)
        id = backend.generate_block_id(be)
        self.failUnless(id.startswith(be.curdir))
        id2 = backend.generate_block_id(be)
        self.failIfEqual(id, id2)

