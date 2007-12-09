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


"""Unit tests for obnam.filelist."""


import os
import unittest


import obnam


class FileComponentTests(unittest.TestCase):

    filename = "README"

    def testCreate(self):
        c = obnam.filelist.create_file_component(self.filename, "pink", 
                                                 "pretty", "black")
        self.check(c)

    def testCreateFromStatResult(self):
        st = os.lstat(self.filename)
        c = obnam.filelist.create_file_component_from_stat(self.filename, st,
                                                           "pink", "pretty",
                                                           "black")
        self.check(c)
        
    def check(self, c):
        self.failIfEqual(c, None)
        subs = c.get_subcomponents()
        self.failUnlessEqual(
          obnam.cmp.first_string_by_kind(subs, obnam.cmp.FILENAME),
          self.filename)

        c_stat = obnam.cmp.first_by_kind(subs, obnam.cmp.STAT)
        c_st = obnam.cmp.parse_stat_component(c_stat)

        st = os.lstat(self.filename)
        self.failUnlessEqual(c_st.st_mode, st.st_mode)
        self.failUnlessEqual(c_st.st_ino, st.st_ino)
        self.failUnlessEqual(c_st.st_dev, st.st_dev)
        self.failUnlessEqual(c_st.st_nlink, st.st_nlink)
        self.failUnlessEqual(c_st.st_uid, st.st_uid)
        self.failUnlessEqual(c_st.st_gid, st.st_gid)
        self.failUnlessEqual(c_st.st_size, st.st_size)
        self.failUnlessEqual(c_st.st_atime, st.st_atime)
        self.failUnlessEqual(c_st.st_mtime, st.st_mtime)
        self.failUnlessEqual(c_st.st_ctime, st.st_ctime)
        self.failUnlessEqual(c_st.st_blocks, st.st_blocks)
        self.failUnlessEqual(c_st.st_blksize, st.st_blksize)
        self.failUnlessEqual(c_st.st_rdev, st.st_rdev)

        self.failUnlessEqual(
            obnam.cmp.first_string_by_kind(subs, obnam.cmp.CONTREF),
            "pink")
        self.failUnlessEqual(
            obnam.cmp.first_string_by_kind(subs, obnam.cmp.SIGREF),
            "pretty")
        self.failUnlessEqual(
            obnam.cmp.first_string_by_kind(subs, obnam.cmp.DELTAREF),
            "black")


class FilelistTests(unittest.TestCase):

    def testCreate(self):
        fl = obnam.filelist.Filelist()
        self.failUnlessEqual(fl.num_files(), 0)

    def testAddFind(self):
        fl = obnam.filelist.Filelist()
        fl.add(".", "pink", None, None)
        self.failUnlessEqual(fl.num_files(), 1)
        c = fl.find(".")
        self.failUnlessEqual(c.get_kind(), obnam.cmp.FILE)

    def testListFiles(self):
        fl = obnam.filelist.Filelist()
        fl.add(".", "pink", None, None)
        self.failUnlessEqual(fl.list_files(), ["."])

    def testAddFileComponent(self):
        fl = obnam.filelist.Filelist()
        fc = obnam.filelist.create_file_component(".", "pink", None, None)
        fl.add_file_component(".", fc)
        self.failUnlessEqual(fl.num_files(), 1)
        c = fl.find(".")
        self.failUnlessEqual(c.get_kind(), obnam.cmp.FILE)

    def testToFromObject(self):
        fl = obnam.filelist.Filelist()
        fl.add(".", "pretty", None, None)
        o = fl.to_object("pink")
        self.failUnlessEqual(o.get_kind(), obnam.obj.FILELIST)
        self.failUnlessEqual(o.get_id(), "pink")
        
        fl2 = obnam.filelist.Filelist()
        fl2.from_object(o)
        self.failIfEqual(fl2, None)
        self.failUnlessEqual(type(fl), type(fl2))
        self.failUnlessEqual(fl2.num_files(), 1)

        c = fl2.find(".")
        self.failIfEqual(c, None)
        self.failUnlessEqual(c.get_kind(), obnam.cmp.FILE)


class FindTests(unittest.TestCase):

    def testFindInodeSuccessful(self):
        pathname = "Makefile"
        fl = obnam.filelist.Filelist()
        fl.add(pathname, "pink", None, None)
        st = os.lstat(pathname)
        c = fl.find_matching_inode(pathname, st)
        subs = c.get_subcomponents()
        stat = obnam.cmp.first_by_kind(subs, obnam.cmp.STAT)
        st2 = obnam.cmp.parse_stat_component(stat)
        self.failUnlessEqual(st.st_mtime, st2.st_mtime)

    def testFindInodeUnsuccessful(self):
        pathname = "Makefile"
        fl = obnam.filelist.Filelist()
        fl.add(pathname, "pink", None, None)
        st = os.lstat(".")
        c = fl.find_matching_inode(pathname, st)
        self.failUnlessEqual(c, None)
        c = fl.find_matching_inode("plirps", st)
        self.failUnlessEqual(c, None)
