# Copyright (C) 2008  Lars Wirzenius <liw@iki.fi>
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


"""Unit tests for obnam.walk."""


import os
import shutil
import tempfile
import unittest

import obnam


class DepthFirstTests(unittest.TestCase):

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.dirs = ["foo", "foo/bar", "foobar"]
        self.dirs = [os.path.join(self.root, x) for x in self.dirs]
        for dir in self.dirs:
            os.mkdir(dir)
        self.dirs.insert(0, self.root)
    
    def tearDown(self):
        shutil.rmtree(self.root)

    def testFindsAllDirs(self):
        dirs = [x[0] for x in obnam.walk.depth_first(self.root)]
        self.failUnlessEqual(sorted(dirs), sorted(self.dirs))

    def prune(self, dirname, dirnames, filenames):
        if "foo" in dirnames:
            dirnames.remove("foo")

    def testFindsAllDirsExceptThePrunedOne(self):
        correct = [x 
                   for x in self.dirs 
                    if not x.endswith("/foo") and not "/foo/" in x]
        dirs = [x[0] 
                for x in obnam.walk.depth_first(self.root, prune=self.prune)]
        self.failUnlessEqual(sorted(dirs), sorted(correct))
