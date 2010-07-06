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


class LocalFSTests(obnamlib.VfsTests, unittest.TestCase):

    def setUp(self):
        self.dirname = tempfile.mkdtemp()
        self.basepath = self.dirname
        self.fs = obnamlib.LocalFS(self.dirname)

    def tearDown(self):
        self.fs.close()
        shutil.rmtree(self.dirname)

    def test_rename_renames_file(self):
        self.fs.write_file('foo', 'xxx')
        self.fs.rename('foo', 'bar')
        self.assertFalse(self.fs.exists('foo'))
        self.assertEqual(self.fs.cat('bar'), 'xxx')

    def test_lstat_returns_result(self):
        self.assert_(self.fs.lstat("."))

    def test_chmod_sets_permissions_correctly(self):
        self.fs.mkdir("foo")
        self.fs.chmod("foo", 0777)
        self.assertEqual(self.fs.lstat("foo").st_mode & 0777, 0777)

    def test_lutimes_sets_times_correctly(self):
        self.fs.mkdir("foo")
        self.fs.lutimes("foo", 1, 2)
        self.assertEqual(self.fs.lstat("foo").st_atime, 1)
        self.assertEqual(self.fs.lstat("foo").st_mtime, 2)

    def test_link_creates_hard_link(self):
        f = self.fs.open("foo", "w")
        f.write("foo")
        f.close()
        self.fs.link("foo", "bar")
        st1 = self.fs.lstat("foo")
        st2 = self.fs.lstat("bar")
        self.assertEqual(st1, st2)

    def test_symlink_creates_soft_link(self):
        self.fs.symlink("foo", "bar")
        target = os.readlink(os.path.join(self.dirname, "bar"))
        self.assertEqual(target, "foo")

    def test_readlink_reads_link_target(self):
        self.fs.symlink("foo", "bar")
        self.assertEqual(self.fs.readlink("bar"), "foo")

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

    def test_write_creates_missing_directories(self):
        self.fs.write_file("foo/bar", "yo")
        self.assertEqual(self.fs.cat("foo/bar"), "yo")

    def test_write_leaves_existing_file_intact(self):
        file(os.path.join(self.dirname, "foo"), "w").write("bar")
        try:
            self.fs.write_file("foo", "foobar")
        except OSError:
            pass
        self.assertEqual(self.fs.cat("foo"), "bar")

    def test_overwrite_creates_new_file_ok(self):
        self.fs.overwrite_file("foo", "bar")
        self.assertEqual(self.fs.cat("foo"), "bar")

    def test_overwrite_renames_existing_file(self):
        self.fs.write_file("foo", "bar")
        self.fs.overwrite_file("foo", "foobar")
        self.assert_(self.fs.exists("foo.bak"))

    def test_overwrite_removes_existing_bak_file(self):
        self.fs.write_file("foo", "bar")
        self.fs.write_file("foo.bak", "baz")
        self.fs.overwrite_file("foo", "foobar")
        self.assertEqual(self.fs.cat("foo.bak"), "bar")

    def test_overwrite_removes_bak_file(self):
        self.fs.write_file("foo", "bar")
        self.fs.overwrite_file("foo", "foobar", make_backup=False)
        self.assertFalse(self.fs.exists("foo.bak"))

    def test_overwrite_is_ok_without_bak(self):
        self.fs.overwrite_file("foo", "foobar", make_backup=False)
        self.assertFalse(self.fs.exists("foo.bak"))

    def test_overwrite_replaces_existing_file(self):
        self.fs.write_file("foo", "bar")
        self.fs.overwrite_file("foo", "foobar")
        self.assertEqual(self.fs.cat("foo"), "foobar")
    
    def test_has_written_nothing_initially(self):
        self.assertEqual(self.fs.written, 0)
    
    def test_write_updates_written(self):
        self.fs.write_file('foo', 'foo')
        self.assertEqual(self.fs.written, 3)
    
    def test_overwrite_updates_written(self):
        self.fs.overwrite_file('foo', 'foo')
        self.assertEqual(self.fs.written, 3)


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
