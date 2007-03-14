# Copyright (C) 2006  Lars Wirzenius <liw@iki.fi>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.


"""Unit tests for obnam.backend"""


import os
import pwd
import shutil
import tempfile
import unittest

import obnam


class GetDefaultUserTest(unittest.TestCase):

    def testLogname(self):
        orig = os.environ.get("LOGNAME", None)
        os.environ["LOGNAME"] = "pink"
        self.failUnlessEqual(obnam.backend.get_default_user(), "pink")
        # Just in case the user's name is "pink"...
        os.environ["LOGNAME"] = "pretty"
        self.failUnlessEqual(obnam.backend.get_default_user(), "pretty")
        if orig is not None:
            os.environ["LOGNAME"] = orig

    def testNoLogname(self):
        orig = os.environ.get("LOGNAME", None)
        del os.environ["LOGNAME"]
        user = obnam.backend.get_default_user()
        uid = pwd.getpwnam(user)[2]
        self.failUnlessEqual(uid, os.getuid())
        if orig is not None:
            os.environ["LOGNAME"] = orig


class ParseStoreUrlTests(unittest.TestCase):

    def test(self):
        cases = (
            ("", None, None, None, ""),
            ("foo", None, None, None, "foo"),
            ("/", None, None, None, "/"),
            ("sftp://host", None, "host", None, ""),
            ("sftp://host/", None, "host", None, "/"),
            ("sftp://host/foo", None, "host", None, "/foo"),
            ("sftp://user@host/foo", "user", "host", None, "/foo"),
            ("sftp://host:22/foo", None, "host", 22, "/foo"),
            ("sftp://user@host:22/foo", "user", "host", 22, "/foo"),
            ("sftp://host/~/foo", None, "host", None, "foo"),
        )
        for case in cases:
            user, host, port, path = obnam.backend.parse_store_url(case[0])
            self.failUnlessEqual(user, case[1])
            self.failUnlessEqual(host, case[2])
            self.failUnlessEqual(port, case[3])
            self.failUnlessEqual(path, case[4])


class DircountTests(unittest.TestCase):

    def testInit(self):
        config = obnam.config.default_config()
        cache = obnam.cache.Cache(config)
        be = obnam.backend.Backend(config, cache)
        self.failUnlessEqual(len(be.dircounts), obnam.backend.LEVELS)
        for i in range(obnam.backend.LEVELS):
            self.failUnlessEqual(be.dircounts[i], 0)
        
    def testIncrementOnce(self):
        config = obnam.config.default_config()
        cache = obnam.cache.Cache(config)
        be = obnam.backend.Backend(config, cache)
        be.increment_dircounts()
        self.failUnlessEqual(be.dircounts, [0, 0, 1])

    def testIncrementMany(self):
        config = obnam.config.default_config()
        cache = obnam.cache.Cache(config)
        be = obnam.backend.Backend(config, cache)
        for i in range(obnam.backend.MAX_BLOCKS_PER_DIR):
            be.increment_dircounts()
        self.failUnlessEqual(be.dircounts, 
                             [0, 0, obnam.backend.MAX_BLOCKS_PER_DIR])

        be.increment_dircounts()
        self.failUnlessEqual(be.dircounts, [0, 1, 0])

        be.increment_dircounts()
        self.failUnlessEqual(be.dircounts, [0, 1, 1])

    def testIncrementTop(self):
        config = obnam.config.default_config()
        cache = obnam.cache.Cache(config)
        be = obnam.backend.Backend(config, cache)
        be.dircounts = [0] + \
            [obnam.backend.MAX_BLOCKS_PER_DIR] * (obnam.backend.LEVELS -1)
        be.increment_dircounts()
        self.failUnlessEqual(be.dircounts, [1, 0, 0])


class LocalBackendBase(unittest.TestCase):

    def setUp(self):
        self.cachedir = "tmp.cachedir"
        self.rootdir = "tmp.rootdir"
        
        os.mkdir(self.cachedir)
        os.mkdir(self.rootdir)
        
        config_list = (
            ("backup", "cache", self.cachedir),
            ("backup", "store", self.rootdir)
        )
    
        self.config = obnam.config.default_config()
        for section, item, value in config_list:
            self.config.set(section, item, value)

        self.cache = obnam.cache.Cache(self.config)

    def tearDown(self):
        shutil.rmtree(self.cachedir)
        shutil.rmtree(self.rootdir)
        del self.cachedir
        del self.rootdir
        del self.config


class InitTests(LocalBackendBase):

    def testInit(self):
        be = obnam.backend.init(self.config, self.cache)
        self.failUnlessEqual(be.url, self.rootdir)


class IdTests(LocalBackendBase):

    def testGenerateBlockId(self):
        be = obnam.backend.init(self.config, self.cache)
        self.failIfEqual(be.blockdir, None)
        id = be.generate_block_id()
        self.failUnless(id.startswith(be.blockdir))
        id2 = be.generate_block_id()
        self.failIfEqual(id, id2)


class UploadTests(LocalBackendBase):

    def testUpload(self):
        self.config.set("backup", "gpg-home", "")
        self.config.set("backup", "gpg-encrypt-to", "")
        self.config.set("backup", "gpg-sign-with", "")
        be = obnam.backend.init(self.config, self.cache)
        id = be.generate_block_id()
        block = "pink is pretty"
        ret = be.upload(id, block)
        self.failUnlessEqual(ret, None)
        self.failUnlessEqual(be.get_bytes_read(), 0)
        self.failUnlessEqual(be.get_bytes_written(), len(block))
        
        pathname = os.path.join(self.rootdir, id)
        self.failUnless(os.path.isfile(pathname))
        
        f = file(pathname, "r")
        data = f.read()
        f.close()
        self.failUnlessEqual(block, data)


class DownloadTests(LocalBackendBase):

    def testOK(self):
        self.config.set("backup", "gpg-home", "")
        self.config.set("backup", "gpg-encrypt-to", "")
        self.config.set("backup", "gpg-sign-with", "")

        be = obnam.backend.init(self.config, self.cache)
        id = be.generate_block_id()
        block = "pink is still pretty"
        be.upload(id, block)
        
        success = be.download(id)
        self.failUnlessEqual(type(success), type(""))
        self.failUnlessEqual(be.get_bytes_read(), len(block))
        self.failUnlessEqual(be.get_bytes_written(), len(block))
        
    def testError(self):
        be = obnam.backend.init(self.config, self.cache)
        id = be.generate_block_id()
        success = be.download(id)
        self.failIfEqual(success, True)


class FileListTests(LocalBackendBase):

    def testFileList(self):
        self.config.set("backup", "gpg-home", "")
        self.config.set("backup", "gpg-encrypt-to", "")
        self.config.set("backup", "gpg-sign-with", "")

        be = obnam.backend.init(self.config, self.cache)
        self.failUnlessEqual(be.list(), [])
        
        id = "pink"
        block = "pretty"
        be.upload(id, block)
        list = be.list()
        self.failUnlessEqual(list, [id])

        filename = os.path.join(self.rootdir, id)
        f = file(filename, "r")
        block2 = f.read()
        f.close()
        self.failUnlessEqual(block, block2)


class RemoveTests(LocalBackendBase):

    def test(self):
        be = obnam.backend.init(self.config, self.cache)
        id = be.generate_block_id()
        block = "pink is still pretty"
        be.upload(id, block)

        self.failUnlessEqual(be.list(), [id])
        
        be.remove(id)
        self.failUnlessEqual(be.list(), [])
