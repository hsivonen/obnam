# Copyright (C) 2008  Lars Wirzenius <liw@liw.fi>
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


import errno
import os
import shutil
import tempfile
import unittest

import obnamlib


class LocalFSTests(unittest.TestCase):

    def setUp(self):
        self.dirname = tempfile.mkdtemp()
        self.fs = obnamlib.LocalFS(self.dirname)

    def tearDown(self):
        shutil.rmtree(self.dirname)

    def test_joins_relative_path_ok(self):
        self.assertEqual(self.fs.join("foo"), 
                         os.path.join(self.dirname, "foo"))

    def test_join_treats_absolute_path_as_relative(self):
        self.assertEqual(self.fs.join("/foo"), 
                         os.path.join(self.dirname, "foo"))

    def test_creates_lock_file(self):
        self.fs.lock("lock")
        self.assert_(self.fs.exists("lock"))
        self.assert_(os.path.exists(os.path.join(self.dirname, "lock")))

    def test_second_lock_fails(self):
        self.fs.lock("lock")
        self.assertRaises(obnamlib.Exception, self.fs.lock, "lock")

    def test_lock_raises_oserror_without_eexist(self):
        def raise_it(relative_path, contents):
            e = OSError()
            e.errno = errno.EAGAIN
            raise e
        self.fs.write_file = raise_it
        self.assertRaises(OSError, self.fs.lock, "foo")

    def test_unlock_removes_lock(self):
        self.fs.lock("lock")
        self.fs.unlock("lock")
        self.assertFalse(self.fs.exists("lock"))
        self.assertFalse(os.path.exists(os.path.join(self.dirname, "lock")))

    def test_exists_returns_false_for_nonexistent_file(self):
        self.assertFalse(self.fs.exists("foo"))

    def test_exists_returns_true_for_existing_file(self):
        file(os.path.join(self.dirname, "foo"), "w").close()
        self.assert_(self.fs.exists("foo"))

    def test_isdir_returns_false_for_nonexistent_file(self):
        self.assertFalse(self.fs.isdir("foo"))

    def test_isdir_returns_false_for_nondir(self):
        file(os.path.join(self.dirname, "foo"), "w").close()
        self.assertFalse(self.fs.isdir("foo"))

    def test_isdir_returns_true_for_existing_dir(self):
        os.mkdir(os.path.join(self.dirname, "foo"))
        self.assert_(self.fs.isdir("foo"))

    def test_opens_existing_file_ok(self):
        file(os.path.join(self.dirname, "foo"), "w").close()
        self.assert_(self.fs.open("foo", "w"))

    def test_open_fails_for_nonexistent_file(self):
        self.assertRaises(IOError, self.fs.open, "foo", "r")

    def test_cat_reads_existing_file_ok(self):
        file(os.path.join(self.dirname, "foo"), "w").write("bar")
        self.assertEqual(self.fs.cat("foo"), "bar")

    def test_cat_fails_for_nonexistent_file(self):
        self.assertRaises(IOError, self.fs.cat, "foo")

    def test_write_file_writes_file_ok(self):
        self.fs.write_file("foo", "bar")
        self.assertEqual(self.fs.cat("foo"), "bar")

    def test_write_fails_if_file_exists_already(self):
        file(os.path.join(self.dirname, "foo"), "w").write("bar")
        self.assertRaises(OSError, self.fs.write_file, "foo", "foobar")

    def test_write_leaves_existing_file_intact(self):
        file(os.path.join(self.dirname, "foo"), "w").write("bar")
        try:
            self.fs.write_file("foo", "foobar")
        except OSError:
            pass
        self.assertEqual(self.fs.cat("foo"), "bar")


class DepthFirstTests(unittest.TestCase):

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.dirs = ["foo", "foo/bar", "foobar"]
        self.dirs = [os.path.join(self.root, x) for x in self.dirs]
        for dir in self.dirs:
            os.mkdir(dir)
        self.dirs.insert(0, self.root)
        self.fs = obnamlib.LocalFS("/")
    
    def tearDown(self):
        shutil.rmtree(self.root)

    def testFindsAllDirs(self):
        dirs = [x[0] for x in self.fs.depth_first(self.root)]
        self.failUnlessEqual(sorted(dirs), sorted(self.dirs))

    def prune(self, dirname, dirnames, filenames):
        if "foo" in dirnames:
            dirnames.remove("foo")

    def testFindsAllDirsExceptThePrunedOne(self):
        correct = [x 
                   for x in self.dirs 
                   if not x.endswith("/foo") and not "/foo/" in x]
        dirs = [x[0] 
                for x in self.fs.depth_first(self.root, prune=self.prune)]
        self.failUnlessEqual(sorted(dirs), sorted(correct))
