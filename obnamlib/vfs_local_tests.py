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
        self.fs.close()
        shutil.rmtree(self.dirname)

    def test_joins_relative_path_ok(self):
        self.assertEqual(self.fs.join("foo"), 
                         os.path.join(self.dirname, "foo"))

    def test_join_treats_absolute_path_as_absolute(self):
        self.assertEqual(self.fs.join("/foo"), "/foo")

    def test_abspath_returns_input_for_absolute_path(self):
        self.assertEqual(self.fs.abspath('/foo/bar'), '/foo/bar')

    def test_abspath_returns_absolute_path_for_relative_input(self):
        self.assertEqual(self.fs.abspath('foo'),
                         os.path.join(self.dirname, 'foo'))

    def test_abspath_normalizes_path(self):
        self.assertEqual(self.fs.abspath('foo/..'), self.dirname)

    def test_getcwd_returns_dirname(self):
        self.assertEqual(self.fs.getcwd(), self.dirname)

    def test_chdir_changes_only_fs_cwd_not_process_cwd(self):
        process_cwd = os.getcwd()
        self.fs.chdir('/')
        self.assertEqual(self.fs.getcwd(), '/')
        self.assertEqual(os.getcwd(), process_cwd)

    def test_chdir_to_nonexistent_raises_exception(self):
        self.assertRaises(OSError, self.fs.chdir, '/foobar')

    def test_chdir_to_relative_works(self):
        pathname = os.path.join(self.dirname, 'foo')
        os.mkdir(pathname)
        self.fs.chdir('foo')
        self.assertEqual(self.fs.getcwd(), pathname)

    def test_chdir_to_dotdot_works(self):
        pathname = os.path.join(self.dirname, 'foo')
        os.mkdir(pathname)
        self.fs.chdir('foo')
        self.fs.chdir('..')
        self.assertEqual(self.fs.getcwd(), self.dirname)

    def test_creates_lock_file(self):
        self.fs.lock("lock")
        self.assert_(self.fs.exists("lock"))
        self.assert_(os.path.exists(os.path.join(self.dirname, "lock")))

    def test_second_lock_fails(self):
        self.fs.lock("lock")
        self.assertRaises(Exception, self.fs.lock, "lock")

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

    def test_mkdir_creates_directory(self):
        self.fs.mkdir("foo")
        self.assert_(os.path.isdir(os.path.join(self.dirname, "foo")))
        
    def test_mkdir_raises_oserror_if_directory_exists(self):
        self.assertRaises(OSError, self.fs.mkdir, ".")

    def test_mkdir_raises_oserror_if_parent_does_not_exist(self):
        self.assertRaises(OSError, self.fs.mkdir, "foo/bar")
    
    def test_makedirs_creates_directory_when_parent_exists(self):
        self.fs.makedirs("foo")
        self.assert_(os.path.isdir(os.path.join(self.dirname, "foo")))
    
    def test_makedirs_creates_directory_when_parent_does_not_exist(self):
        self.fs.makedirs("foo/bar")
        self.assert_(os.path.isdir(os.path.join(self.dirname, "foo/bar")))

    def test_rmdir_removes_directory(self):
        self.fs.mkdir('foo')
        self.fs.rmdir('foo')
        self.assertFalse(self.fs.exists('foo'))

    def test_rmdir_raises_oserror_if_directory_does_not_exist(self):
        self.assertRaises(OSError, self.fs.rmdir, 'foo')

    def test_rmdir_raises_oserror_if_directory_is_not_empty(self):
        self.fs.mkdir('foo')
        self.fs.write_file('foo/bar', '')
        self.assertRaises(OSError, self.fs.rmdir, 'foo')

    def test_rmtree_removes_directory_tree(self):
        self.fs.mkdir('foo')
        self.fs.write_file('foo/bar', '')
        self.fs.rmtree('foo')
        self.assertFalse(self.fs.exists('foo'))

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

    def test_overwrite_replaces_existing_file(self):
        self.fs.write_file("foo", "bar")
        self.fs.overwrite_file("foo", "foobar")
        self.assertEqual(self.fs.cat("foo"), "foobar")


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
