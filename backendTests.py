import ConfigParser
import tempfile
import unittest

import backend


class InitTests(unittest.TestCase):

    def testInit(self):
        tempdir = tempfile.mkdtemp()
        config = ConfigParser.ConfigParser()
        config.add_section("local-backend")
        config.set("local-backend", "root", tempdir)
        be = backend.init(config)
        self.failUnlessEqual(be.local_root, tempdir)
