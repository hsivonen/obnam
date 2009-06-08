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


import stat
import unittest

import mox

import obnamlib


class DummyObject(object):

    """Dummy object for aiding in some unit tests."""

    def __init__(self, id):
        self.id = id


class DummyIdCache(object):

    def __getitem__(self, numeric_id):
        return ""


class IdCacheTests(unittest.TestCase):

    def setUp(self):
        self.cache = obnamlib.ui_cli_backup.IdCache()
        self.cache.lookup_name = lambda x: str(x)
        
    def test_finds_id_the_first_time(self):
        self.assertEqual(self.cache[42], "42")
        
    def test_finds_id_the_second_time(self):
        self.cache[42] = "foo" # make sure it's there, and different from
                               # what lookup_name returns
        self.assertEqual(self.cache[42], "foo")

    def test_returns_empty_if_id_is_not_found(self):
        def notfound(x):
            raise KeyError()
        self.cache.lookup_name = notfound
        self.assertEqual(self.cache[42], "")


class BackupCommandTests(unittest.TestCase):

    def setUp(self):
        self.mox = mox.Mox()
        self.cmd = obnamlib.BackupCommand()
        self.cmd.store = self.mox.CreateMock(obnamlib.Store)
        self.cmd.fs = self.mox.CreateMock(obnamlib.VirtualFileSystem)
        self.cmd.prevgen_lookupper = obnamlib.ui_cli_backup.DummyLookupper()
        self.cmd.progress = obnamlib.ProgressReporter(silent=True)
        self.cmd.uid_cache = DummyIdCache()
        self.cmd.gid_cache = DummyIdCache()

    def test_backs_up_new_symlink_correctly(self):
        st = obnamlib.make_stat()
        self.cmd.fs.readlink("foo").AndReturn("target")
        self.mox.ReplayAll()
        symlink = self.cmd.backup_new_symlink("foo", st)
        self.mox.VerifyAll()
        self.assertEqual(symlink.filename, "foo")
        self.assertEqual(symlink.stat, st)
        self.assertEqual(symlink.symlink_target, "target")

    def test_backs_up_new_file_correctly(self):
        st = obnamlib.make_stat()

        f = self.mox.CreateMock(file)
        fc = self.mox.CreateMock(obnamlib.FileContents)
        fc.id = "contentsid"

        self.cmd.fs.open("foo", "r").AndReturn(f)
        self.cmd.store.put_contents(f, self.cmd.PART_SIZE).AndReturn(fc)
        f.close()

        self.mox.ReplayAll()
        new_file = self.cmd.backup_new_file("foo", st)
        self.mox.VerifyAll()
        self.assertEqual(new_file.filename, "foo")
        self.assertEqual(new_file.stat, st)
        self.assertEqual(new_file.contref, fc.id)
        self.assertEqual(new_file.sigref, None)
        self.assertEqual(new_file.deltaref, None)

    def test_backs_up_filegroups_correctly(self):
        fg = self.mox.CreateMock(obnamlib.FileGroup)
        fg.components = self.mox.CreateMock(list)

        # Backup foo, a regular file.
        self.cmd.fs.lstat("foo").AndReturn(
            obnamlib.make_stat(st_mode=stat.S_IFREG))
        f = self.mox.CreateMock(file)
        self.cmd.fs.open("foo", "r").AndReturn(f)
        cont = self.mox.CreateMock(obnamlib.FileContents)
        cont.id = "filecontents.id"
        self.cmd.store.put_contents(f, self.cmd.PART_SIZE).AndReturn(cont)
        f.close()

        # The FileGroup gets created after the first file to be added,
        # so it doesn't created if there is nothing to add.
        self.cmd.store.new_object(kind=obnamlib.FILEGROUP).AndReturn(fg)
        fg.components.append(mox.IsA(obnamlib.Component))
        
        # Backup bar, a symlink.
        self.cmd.fs.lstat("bar").AndReturn(
            obnamlib.make_stat(st_mode=stat.S_IFLNK))
        self.cmd.fs.readlink("bar").AndReturn("target")
        fg.components.append(mox.IsA(obnamlib.Component))
        
        # Backup foobar, something else.
        self.cmd.fs.lstat("foobar").AndReturn(obnamlib.make_stat())
        fg.components.append(mox.IsA(obnamlib.Component))
        
        # Put FileGroup in store.
        self.cmd.store.put_object(fg)        

        self.mox.ReplayAll()
        ret = self.cmd.backup_new_files_as_groups(["foo", "bar", "foobar"])
        self.mox.VerifyAll()
        self.assertEqual(ret, [fg])

    def test_backs_up_directory_correctly(self):
        filenames = []
        def mock_backup_files(names):
            for name in names:
                filenames.append(name)
            return [DummyObject("fg")]
        self.cmd.backup_new_files_as_groups = mock_backup_files

        dir = self.mox.CreateMock(obnamlib.Dir)
        subdirs = [DummyObject(id) for id in ["dir1", "dir2"]]

        self.cmd.store.new_object(obnamlib.DIR).AndReturn(dir)
        self.cmd.store.put_object(dir)

        self.mox.ReplayAll()
        lstat = lambda *args: obnamlib.make_stat(st_mode=1, st_uid=2)
        ret = self.cmd.backup_dir("foo", subdirs, ["file1", "file2"],
                                  lstat=lstat)
        self.mox.VerifyAll()
        self.assertEqual(ret, dir)
        self.assertEqual(ret.name, "foo")
        self.assertEqual(ret.stat, obnamlib.make_stat(st_mode=1, st_uid=2))
        self.assertEqual(ret.dirrefs, ["dir1", "dir2"])
        self.assertEqual(ret.fgrefs, ["fg"])
        self.assertEqual(filenames, ["foo/file1", "foo/file2"])

    def test_backs_up_empty_directory_correctly(self):
        self.cmd.backup_new_files_as_groups = lambda *args: []

        lstat = lambda *args: obnamlib.make_stat()
        ret = self.cmd.backup_dir("foo", [], [], lstat=lstat)
        self.assertNotEqual(ret.stat, None)
        self.assertEqual(ret.dirrefs, [])
        self.assertEqual(ret.fgrefs, [])

    def test_backs_up_recursively_empty_directory_correctly(self):
        dir = self.mox.CreateMock(obnamlib.Dir)
        dir.id = "dirid"
        self.cmd.backup_dir = lambda *args: dir
        self.cmd.fs = self.mox.CreateMock(obnamlib.VirtualFileSystem)

        self.cmd.fs.depth_first("foo").AndReturn([("foo", [], [])])
        self.cmd.it_is_snapshot_time = lambda: False

        self.mox.ReplayAll()
        ret = [x for x in self.cmd.backup_recursively("foo")]
        self.assertEqual(len(ret), 1)
        self.mox.VerifyAll()
        self.assertEquals(ret[0], dir)

    def test_backs_up_recursively_non_empty_directory_correctly(self):
        args = []
        results = []
        self.count = 0
        def mock_backup_dir(dirname, subdirs, filenames):
            args.append((dirname, subdirs, filenames))
            self.count += 1
            dir = obnamlib.Dir(id=("%s" % self.count), name=dirname)
            results.append(dir)
            return dir
        self.cmd.backup_dir = mock_backup_dir
        self.cmd.it_is_snapshot_time = lambda: False

        tree = [
            ("foo/dir1", [], ["file2"]),
            ("foo", ["dir1"], ["file1"]),
            ]
        self.cmd.fs = self.mox.CreateMock(obnamlib.VirtualFileSystem)
        self.cmd.fs.depth_first("foo").AndReturn(tree)

        self.mox.ReplayAll()
        ret = [x for x in self.cmd.backup_recursively("foo")]
        self.assertEqual(len(ret), 1)
        ret = ret[0]
        self.mox.VerifyAll()
        self.assertEquals(ret, results[-1])
        self.assertEquals(args, 
                          [("foo/dir1", [], ["file2"]),
                           ("foo", [results[0]], ["file1"]),
                           ])

    def test_backs_up_mixed_roots(self):
        self.count = 0

        dirnames = []
        dirrefs = []
        def dummy_backup_recursively(dirname):
            dirnames.append(dirname)
            self.count += 1
            dir = obnamlib.Dir(id="%s" % self.count)
            dirrefs.append(dir.id)
            yield dir
        self.cmd.backup_recursively = dummy_backup_recursively

        filenames = []
        fgrefs = []
        def dummy_backup_groups(names):
            for name in names:
                filenames.append(name)
            self.count += 1
            fg = obnamlib.FileGroup(id="%s" % self.count)
            fgrefs.append(fg.id)
            return [fg]
        self.cmd.backup_new_files_as_groups = dummy_backup_groups
        
        self.cmd.host = self.mox.CreateMock(obnamlib.Host)
        self.cmd.host.genrefs = []
        self.cmd.host.fgrefs = []

        gen = self.mox.CreateMock(obnamlib.Generation)
        gen.dirrefs = []
        gen.fgrefs = []
        gen.id = "gen.id"
        self.cmd.store.new_object(obnamlib.GEN).AndReturn(gen)
        self.cmd.fs.isdir("dir").AndReturn(True)
        self.cmd.fs.isdir("file").AndReturn(False)
        self.cmd.store.put_object(gen)
        self.cmd.store.commit(self.cmd.host, close=False)
        
        self.mox.ReplayAll()
        gen = self.cmd.backup_generation(["dir", "file"])
        self.mox.VerifyAll()
        self.assertEqual(dirnames, ["dir"])
        self.assertEqual(filenames, ["file"])
        self.assertEqual(len(dirrefs), 1)
        self.assertEqual(len(fgrefs), 1)
        self.assertEqual(gen.dirrefs, dirrefs)
        self.assertEqual(gen.fgrefs, fgrefs)

    def test_backs_up_correctly(self):
        def mock_backup_generation(roots):
            return DummyObject("genid")
        self.cmd.backup_generation = mock_backup_generation

        host = self.mox.CreateMock(obnamlib.Host)
        host.genrefs = []

        self.cmd.store.get_host("foo").AndReturn(host)
        self.cmd.store.commit(host)

        self.mox.ReplayAll()
        self.cmd.backup("foo", ["bar", "foobar"])
        self.mox.VerifyAll()
        
    def test_lists_no_ancestor_for_root_directory(self):
        self.assertEqual(self.cmd.list_ancestors("/"), [])

    def test_lists_only_root_for_subdir_of_root(self):
        self.assertEqual(self.cmd.list_ancestors("/foo"), ["/"])

    def test_lists_all_ancestors_of_long_path(self):
        self.assertEqual(self.cmd.list_ancestors("/foo/bar/foobar"), 
                         ["/foo/bar", "/foo", "/"])

    def test_list_ancestors_ignores_period(self):
        self.assertEqual(self.cmd.list_ancestors("/foo/bar/./foobar"), 
                         ["/foo/bar", "/foo", "/"])

    def test_list_ancestors_interprets_two_periods(self):
        self.assertEqual(self.cmd.list_ancestors("/foo/bar/../foobar"), 
                         ["/foo", "/"])

    def test_lists_ancestors_for_relative_path(self):
        self.assertEqual(self.cmd.list_ancestors("foo/bar"), ["foo"])

    def test_lists_no_ancestors_for_single_element_relative_path(self):
        self.assertEqual(self.cmd.list_ancestors("foo"), [])

