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
        subs = obnam.cmp.get_subcomponents(c)
        self.failUnlessEqual(
          obnam.cmp.first_string_by_kind(subs, obnam.cmp.FILENAME),
          self.filename)

        st = os.lstat(self.filename)
        self.failUnlessEqual(
          obnam.cmp.first_varint_by_kind(subs, obnam.cmp.ST_MODE),
          st.st_mode)
        self.failUnlessEqual(
          obnam.cmp.first_varint_by_kind(subs, obnam.cmp.ST_INO),
          st.st_ino)
        self.failUnlessEqual(
          obnam.cmp.first_varint_by_kind(subs, obnam.cmp.ST_DEV),
          st.st_dev)
        self.failUnlessEqual(
          obnam.cmp.first_varint_by_kind(subs, obnam.cmp.ST_NLINK),
          st.st_nlink)
        self.failUnlessEqual(
          obnam.cmp.first_varint_by_kind(subs, obnam.cmp.ST_UID),
          st.st_uid)
        self.failUnlessEqual(
          obnam.cmp.first_varint_by_kind(subs, obnam.cmp.ST_GID),
          st.st_gid)
        self.failUnlessEqual(
          obnam.cmp.first_varint_by_kind(subs, obnam.cmp.ST_SIZE),
          st.st_size)
        self.failUnlessEqual(
          obnam.cmp.first_varint_by_kind(subs, obnam.cmp.ST_ATIME),
          st.st_atime)
        self.failUnlessEqual(
          obnam.cmp.first_varint_by_kind(subs, obnam.cmp.ST_MTIME),
          st.st_mtime)
        self.failUnlessEqual(
          obnam.cmp.first_varint_by_kind(subs, obnam.cmp.ST_CTIME),
          st.st_ctime)
        self.failUnlessEqual(
          obnam.cmp.first_varint_by_kind(subs, obnam.cmp.ST_BLOCKS),
          st.st_blocks)
        self.failUnlessEqual(
          obnam.cmp.first_varint_by_kind(subs, 
            obnam.cmp.ST_BLKSIZE),
          st.st_blksize)

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
        fl = obnam.filelist.create()
        self.failUnlessEqual(obnam.filelist.num_files(fl), 0)

    def testAddFind(self):
        fl = obnam.filelist.create()
        obnam.filelist.add(fl, ".", "pink", None, None)
        self.failUnlessEqual(obnam.filelist.num_files(fl), 1)
        c = obnam.filelist.find(fl, ".")
        self.failUnlessEqual(obnam.cmp.get_kind(c), obnam.cmp.FILE)

    def testAddFileComponent(self):
        fl = obnam.filelist.create()
        fc = obnam.filelist.create_file_component(".", "pink", None, None)
        obnam.filelist.add_file_component(fl, ".", fc)
        self.failUnlessEqual(obnam.filelist.num_files(fl), 1)
        c = obnam.filelist.find(fl, ".")
        self.failUnlessEqual(obnam.cmp.get_kind(c), obnam.cmp.FILE)

    def testToFromObject(self):
        fl = obnam.filelist.create()
        obnam.filelist.add(fl, ".", "pretty", None, None)
        o = obnam.filelist.to_object(fl, "pink")
        self.failUnlessEqual(obnam.obj.get_kind(o), 
                             obnam.obj.FILELIST)
        self.failUnlessEqual(obnam.obj.get_id(o), "pink")
        
        fl2 = obnam.filelist.from_object(o)
        self.failIfEqual(fl2, None)
        self.failUnlessEqual(type(fl), type(fl2))
        self.failUnlessEqual(obnam.filelist.num_files(fl2), 1)

        c = obnam.filelist.find(fl2, ".")
        self.failIfEqual(c, None)
        self.failUnlessEqual(obnam.cmp.get_kind(c), obnam.cmp.FILE)


class FindTests(unittest.TestCase):

    def testFindInodeSuccessful(self):
        pathname = "Makefile"
        fl = obnam.filelist.create()
        obnam.filelist.add(fl, pathname, "pink", None, None)
        st = os.lstat(pathname)
        c = obnam.filelist.find_matching_inode(fl, pathname, st)
        subs = obnam.cmp.get_subcomponents(c)
        self.failUnlessEqual(
          obnam.cmp.first_varint_by_kind(subs, obnam.cmp.ST_MTIME),
          st.st_mtime)

    def testFindInodeUnsuccessful(self):
        pathname = "Makefile"
        fl = obnam.filelist.create()
        obnam.filelist.add(fl, pathname, "pink", None, None)
        st = os.lstat(".")
        c = obnam.filelist.find_matching_inode(fl, pathname, st)
        self.failUnlessEqual(c, None)
