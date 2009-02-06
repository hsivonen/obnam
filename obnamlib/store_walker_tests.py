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


import mox
import unittest

import obnamlib


class StoreWalkerTests(unittest.TestCase):

    def setUp(self):
        self.mox = mox.Mox()
        self.store = self.mox.CreateMock(obnamlib.Store)
        self.host = self.mox.CreateMock(obnamlib.Host)
        self.gen = self.mox.CreateMock(obnamlib.Generation)
        self.gen.fgrefs = []
        self.gen.dirrefs = []
        self.walker = obnamlib.StoreWalker(self.store, self.host, self.gen)
        
    def test_root_files_is_empty_for_empty_generation(self):
        self.assertEqual(self.walker.root_files, [])

    def test_root_files_catches_files_at_generation_root(self):
        self.gen.fgrefs = ["fg.id"]
        fg = self.mox.CreateMock(obnamlib.FileGroup)
        fg.files = ["foo", "bar"]
        self.store.get_object(self.host, "fg.id").AndReturn(fg)
        self.mox.ReplayAll()
        self.assertEqual(self.walker.root_files, ["foo", "bar"])
        self.mox.VerifyAll()
        
    def test_root_dirs_is_empty_for_empty_generation(self):
        self.assertEqual(self.walker.root_dirs, [])

    def test_root_dirs_catches_dirs_at_generation_root(self):
        self.gen.dirrefs = ["dir.id"]
        dir = self.mox.CreateMock(obnamlib.Dir)
        dir.name = "foo"
        self.store.get_object(self.host, "dir.id").AndReturn(dir)
        self.mox.ReplayAll()
        self.assertEqual(self.walker.root_dirs, ["foo"])
        self.mox.VerifyAll()

    def test_walk_balks_at_nondirectory_as_root(self):
        
        class EverythingIsAFileLookupper(object):
            def is_file(self, name):
                return True

        self.walker.lookupper = EverythingIsAFileLookupper()
        self.assertRaises(obnamlib.Exception, list, self.walker.walk("file"))

    def create_mock_dir(self, name, subdirs, filenames):
        dir = self.mox.CreateMock(obnamlib.Dir)
        dir.name = name
        dir.id = "%s.id" % name
        dir.dirrefs = [x.id for x in subdirs]
        fg = self.mox.CreateMock(obnamlib.FileGroup)
        fg.id = "%s.fg.id" % name
        fg.files = filenames
        dir.fg = fg
        dir.fgrefs = [fg.id]
        return dir

    def test_walk_goes_everywhere_and_sees_everything(self):
        dir3 = self.create_mock_dir("dir3", [], ["file2"])
        dir2 = self.create_mock_dir("dir2", [], [])
        dir = self.create_mock_dir("dir", [dir2, dir3], ["file1"])
        
        class MockLookupper(object):
            def __init__(self):
                self.dict = {
                    dir.name: dir,
                    "%s/%s" % (dir.name, dir2.name): dir2,
                    "%s/%s" % (dir.name, dir3.name): dir3,
                }

            def is_file(self, name):
                return False
                
            def get_dir(self, name):
                return self.dict[name]

        self.walker.lookupper = MockLookupper()

        self.store.get_object(self.host, "dir2.id").AndReturn(dir2)
        self.store.get_object(self.host, "dir3.id").AndReturn(dir3)
        self.store.get_object(self.host, "dir.fg.id").AndReturn(dir.fg)
        self.store.get_object(self.host, "dir2.fg.id").AndReturn(dir2.fg)
        self.store.get_object(self.host, "dir3.fg.id").AndReturn(dir3.fg)

        self.mox.ReplayAll()
        list = [x for x in self.walker.walk("dir")]
        self.mox.VerifyAll()
        self.assertEqual(list, 
                         [("dir", ["dir2", "dir3"], ["file1"]),
                          ("dir/dir2", [], []),
                          ("dir/dir3", [], ["file2"])])

    def test_walk_generation_goes_everywhere_and_sees_everything(self):
        dir3 = self.create_mock_dir("dir3", [], ["file2"])
        dir2 = self.create_mock_dir("dir2", [], [])
        dir = self.create_mock_dir("dir", [dir2, dir3], ["file1"])
        
        class MockLookupper(object):
            def __init__(self):
                self.dict = {
                    dir.name: dir,
                    "%s/%s" % (dir.name, dir2.name): dir2,
                    "%s/%s" % (dir.name, dir3.name): dir3,
                }

            def is_file(self, name):
                return False
                
            def get_dir(self, name):
                return self.dict[name]

        self.walker.lookupper = MockLookupper()
        self.walker._root_files = ["foo"]
        self.walker._root_dirs = [dir.name]

        self.store.get_object(self.host, "dir2.id").AndReturn(dir2)
        self.store.get_object(self.host, "dir3.id").AndReturn(dir3)
        self.store.get_object(self.host, "dir.fg.id").AndReturn(dir.fg)
        self.store.get_object(self.host, "dir2.fg.id").AndReturn(dir2.fg)
        self.store.get_object(self.host, "dir3.fg.id").AndReturn(dir3.fg)

        self.mox.ReplayAll()
        list = [x for x in self.walker.walk_generation()]
        self.mox.VerifyAll()
        self.assertEqual(list, 
                         [(".", [], ["foo"]),
                          ("dir", ["dir2", "dir3"], ["file1"]),
                          ("dir/dir2", [], []),
                          ("dir/dir3", [], ["file2"])])
