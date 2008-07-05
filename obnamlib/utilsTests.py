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


"""Unit tests for utils.py in obnamlib."""


import os
import shutil
import tempfile
import unittest

import obnamlib


class MakeStatResultTests(unittest.TestCase):

    def testSetsEverytingToZeroByDefault(self):
        st = obnamlib.make_stat_result()
        self.failUnlessEqual(st.st_mode, 0)
        self.failUnlessEqual(st.st_ino, 0)
        self.failUnlessEqual(st.st_dev, 0)
        self.failUnlessEqual(st.st_nlink, 0)
        self.failUnlessEqual(st.st_uid, 0)
        self.failUnlessEqual(st.st_gid, 0)
        self.failUnlessEqual(st.st_size, 0)
        self.failUnlessEqual(st.st_atime, 0)
        self.failUnlessEqual(st.st_mtime, 0)
        self.failUnlessEqual(st.st_ctime, 0)
        self.failUnlessEqual(st.st_blocks, 0)
        self.failUnlessEqual(st.st_blksize, 0)
        self.failUnlessEqual(st.st_rdev, 0)

    def testSetsDesiredFieldToDesiredValue(self):
        st = obnamlib.make_stat_result(st_size=12765)
        self.failUnlessEqual(st.st_size, 12765)


class CreateFileTests(unittest.TestCase):

    def setUp(self):
        self.dirname = tempfile.mkdtemp()
        self.filename = os.path.join(self.dirname, "foo")

    def tearDown(self):
        if os.path.exists(self.dirname):
            shutil.rmtree(self.dirname)

    def cat(self, filename):
        return file(filename).read()

    def testCreatesNewFile(self):
        obnamlib.create_file(self.filename, "bar")
        self.failUnless(os.path.exists(self.filename))

    def testNewFileHasRightContents(self):
        obnamlib.create_file(self.filename, "bar")
        self.failUnlessEqual(self.cat(self.filename), "bar")
    
    def testOverwritesExistingFileWithRightContents(self):
        obnamlib.create_file(self.filename, "bar")
        obnamlib.create_file(self.filename, "foobar")
        self.failUnlessEqual(self.cat(self.filename), "foobar")


class ReadFileTests(unittest.TestCase):

    def testReturnsTheCorrectContents(self):
        (fd, filename) = tempfile.mkstemp()
        os.write(fd, "foo")
        os.close(fd)
        self.failUnlessEqual(obnamlib.read_file(filename), "foo")

