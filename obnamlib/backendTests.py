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


"""Unit tests for obnamlib.backend"""


import os
import pwd
import shutil
import stat
import tempfile
import unittest

import obnamlib


class GetDefaultUserTest(unittest.TestCase):

    def setUp(self):
        self.orig = os.environ.get("LOGNAME", None)
    
    def tearDown(self):
        if self.orig is not None:
            os.environ["LOGNAME"] = self.orig
        else:
            del os.environ["LOGNAME"]

    def testLogname(self):
        os.environ["LOGNAME"] = "pink"
        self.failUnlessEqual(obnamlib.backend.get_default_user(), "pink")

    def testLognameWhenItIsPink(self):
        # Just in case the user's name is "pink"...
        os.environ["LOGNAME"] = "pretty"
        self.failUnlessEqual(obnamlib.backend.get_default_user(), "pretty")

    def testNoLogname(self):
        del os.environ["LOGNAME"]
        user = obnamlib.backend.get_default_user()
        uid = pwd.getpwnam(user)[2]
        self.failUnlessEqual(uid, os.getuid())


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
            user, host, port, path = obnamlib.backend.parse_store_url(case[0])
            self.failUnlessEqual(user, case[1])
            self.failUnlessEqual(host, case[2])
            self.failUnlessEqual(port, case[3])
            self.failUnlessEqual(path, case[4])


class UseGpgTests(unittest.TestCase):

    def setUp(self):
        self.config = obnamlib.config.default_config()
        self.config.set("backup", "gpg-encrypt-to", "")
        self.cache = obnamlib.Cache(self.config)
        self.be = obnamlib.backend.Backend(self.config, self.cache)

    def testDoNotUseByDefault(self):
        self.failIf(self.be.use_gpg())

    def testUseIfRequested(self):
        self.config.set("backup", "gpg-encrypt-to", "pink")
        self.failUnless(self.be.use_gpg())

    def testDoNotUseEvenIfRequestedIfNoGpgIsSet(self):
        self.config.set("backup", "gpg-encrypt-to", "pink")
        self.config.set("backup", "no-gpg", "true")
        self.failIf(self.be.use_gpg())


class DircountTests(unittest.TestCase):

    def setUp(self):
        self.config = obnamlib.config.default_config()
        self.cache = obnamlib.Cache(self.config)
        self.be = obnamlib.backend.Backend(self.config, self.cache)

    def testInit(self):
        self.failUnlessEqual(len(self.be.dircounts), obnamlib.backend.LEVELS)
        for i in range(obnamlib.backend.LEVELS):
            self.failUnlessEqual(self.be.dircounts[i], 0)
        
    def testIncrementOnce(self):
        self.be.increment_dircounts()
        self.failUnlessEqual(self.be.dircounts, [0, 0, 1])

    def testIncrementMany(self):
        for i in range(obnamlib.backend.MAX_BLOCKS_PER_DIR):
            self.be.increment_dircounts()
        self.failUnlessEqual(self.be.dircounts, 
                             [0, 0, obnamlib.backend.MAX_BLOCKS_PER_DIR])

        self.be.increment_dircounts()
        self.failUnlessEqual(self.be.dircounts, [0, 1, 0])

        self.be.increment_dircounts()
        self.failUnlessEqual(self.be.dircounts, [0, 1, 1])

    def testIncrementTop(self):
        self.be.dircounts = [0] + \
            [obnamlib.backend.MAX_BLOCKS_PER_DIR] * (obnamlib.backend.LEVELS -1)
        self.be.increment_dircounts()
        self.failUnlessEqual(self.be.dircounts, [1, 0, 0])


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
    
        self.config = obnamlib.config.default_config()
        for section, item, value in config_list:
            self.config.set(section, item, value)

        self.cache = obnamlib.Cache(self.config)

    def tearDown(self):
        shutil.rmtree(self.cachedir)
        shutil.rmtree(self.rootdir)
        del self.cachedir
        del self.rootdir
        del self.config


class InitTests(LocalBackendBase):

    def testInit(self):
        be = obnamlib.backend.init(self.config, self.cache)
        self.failUnlessEqual(be.url, self.rootdir)


class IdTests(LocalBackendBase):

    def testGenerateBlockId(self):
        be = obnamlib.backend.init(self.config, self.cache)
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
        be = obnamlib.backend.init(self.config, self.cache)
        id = be.generate_block_id()
        block = "pink is pretty"
        ret = be.upload_block(id, block, False)
        self.failUnlessEqual(ret, None)
        self.failUnlessEqual(be.get_bytes_read(), 0)
        self.failUnlessEqual(be.get_bytes_written(), len(block))
        
        pathname = os.path.join(self.rootdir, id)
        self.failUnless(os.path.isfile(pathname))
        
        st = os.lstat(pathname)
        self.failUnlessEqual(stat.S_IMODE(st.st_mode), 0600)
        
        f = file(pathname, "r")
        data = f.read()
        f.close()
        self.failUnlessEqual(block, data)

    def testUploadToCache(self):
        cachedir = self.config.get("backup", "cache")
        self.failUnlessEqual(os.listdir(cachedir), [])

        self.config.set("backup", "gpg-home", "")
        self.config.set("backup", "gpg-encrypt-to", "")
        self.config.set("backup", "gpg-sign-with", "")
        self.config.set("backup", "cache", cachedir)

        be = obnamlib.backend.init(self.config, self.cache)
        id = be.generate_block_id()
        block = "pink is pretty"
        ret = be.upload_block(id, block, True)
        self.failIfEqual(os.listdir(cachedir), [])


class DownloadTests(LocalBackendBase):

    def testOK(self):
        self.config.set("backup", "gpg-home", "sample-gpg-home")
        self.config.set("backup", "gpg-encrypt-to", "490C9ED1")
        self.config.set("backup", "gpg-sign-with", "490C9ED1")

        be = obnamlib.backend.init(self.config, self.cache)
        id = be.generate_block_id()
        block = "pink is still pretty"
        be.upload_block(id, block, False)
        
        downloaded_block = be.download_block(id)
        self.failUnlessEqual(block, downloaded_block)
        self.failUnlessEqual(be.get_bytes_read(), 
                             be.get_bytes_written())
        
    def testError(self):
        be = obnamlib.backend.init(self.config, self.cache)
        id = be.generate_block_id()
        self.failUnlessRaises(IOError, be.download_block, id)


class FileListTests(LocalBackendBase):

    def testFileList(self):
        self.config.set("backup", "gpg-home", "")
        self.config.set("backup", "gpg-encrypt-to", "")
        self.config.set("backup", "gpg-sign-with", "")

        be = obnamlib.backend.init(self.config, self.cache)
        self.failUnlessEqual(be.list(), [])
        
        id = "pink"
        block = "pretty"
        be.upload_block(id, block, False)
        list = be.list()
        self.failUnlessEqual(list, [id])

        filename = os.path.join(self.rootdir, id)
        f = file(filename, "r")
        block2 = f.read()
        f.close()
        self.failUnlessEqual(block, block2)


class RemoveTests(LocalBackendBase):

    def test(self):
        be = obnamlib.backend.init(self.config, self.cache)
        id = be.generate_block_id()
        block = "pink is still pretty"
        be.upload_block(id, block, False)

        self.failUnlessEqual(be.list(), [id])
        
        be.remove(id)
        self.failUnlessEqual(be.list(), [])
