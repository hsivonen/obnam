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


"""Unit tests for obnamlib.cache"""


import os
import shutil
import tempfile
import unittest

import obnamlib


class CacheTests(unittest.TestCase):

    def setUp(self):
        self.cachedir = tempfile.mkdtemp()
        self.config = obnamlib.config.default_config()
        self.config.set("backup", "cache", self.cachedir)
        self.cache = obnamlib.Cache(self.config)

    def tearDown(self):
        if os.path.exists(self.cachedir):
            shutil.rmtree(self.cachedir)

    def testGetsNameOfBlockInCacheRight(self):
        self.failUnlessEqual(self.cache.cache_pathname("pink/pretty"),
                             os.path.join(self.cachedir, "pink/pretty"))

    def testPutsBlockIntoCacheWithRightName(self):
        self.cache.put_block("pink", "pretty")
        self.failUnless(os.path.isfile(self.cache.cache_pathname("pink")))
        
    def testPutsBlockIntoCacheWithRightContents(self):
        self.cache.put_block("pink", "pretty")
        pathname = self.cache.cache_pathname("pink")
        self.failUnlessEqual(obnamlib.read_file(pathname), "pretty")

    def testPutsBlockIntoCacheWhenIdHasSubdirs(self):
        self.cache.put_block("pink/pretty", "")
        pathname = self.cache.cache_pathname("pink/pretty")
        self.failUnless(os.path.isfile(pathname))

    def testReturnsNoneWhenReadingNonexistingBlock(self):
        self.failUnlessEqual(self.cache.get_block("pink"), None)

    def testReturnsBlockContentsWhenRequested(self):
        self.cache.put_block("pink", "pretty")
        self.failUnlessEqual(self.cache.get_block("pink"), "pretty")

