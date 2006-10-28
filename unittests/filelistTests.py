import unittest


import wibbrlib


class FileComponentTests(unittest.TestCase):

    def testCreate(self):
        c = wibbrlib.filelist.create_file_component(".")
        self.failIfEqual(c, None)
        subs = wibbrlib.cmp.get_subcomponents(c)
        self.failUnlessEqual(
          wibbrlib.cmp.first_string_by_kind(subs, wibbrlib.cmp.CMP_FILENAME),
          ".")


class FilelistTests(unittest.TestCase):

    def testCreate(self):
        fl = wibbrlib.filelist.create()
        self.failUnlessEqual(wibbrlib.filelist.num_files(fl), 0)

    def testAddFind(self):
        fl = wibbrlib.filelist.create()
        wibbrlib.filelist.add(fl, ".")
        self.failUnlessEqual(wibbrlib.filelist.num_files(fl), 1)
        c = wibbrlib.filelist.find(fl, ".")
        self.failIfEqual(c, None)
