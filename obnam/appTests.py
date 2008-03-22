# Copyright (C) 2006, 2007  Lars Wirzenius <liw@iki.fi>
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


"""Unit tests for app.py."""


import os
import re
import tempfile
import unittest

import obnam


class ApplicationTests(unittest.TestCase):

    def make_tempfiles(self, n):
        list = []
        for i in range(n):
            if (i % 2) == 0:
                list.append(tempfile.mkdtemp())
            else:
                fd, name = tempfile.mkstemp()
                os.close(fd)
                list.append(name)
        return list

    def remove_tempfiles(self, filenames):
        for name in filenames:
            if os.path.isdir(name):
                os.rmdir(name)
            else:
                os.remove(name)

    def setUp(self):
        context = obnam.context.Context()
        self.app = obnam.Application(context)
        
        self.tempfiles = self.make_tempfiles(obnam.app.MAX_PER_FILEGROUP + 1)
        
    def tearDown(self):
        self.remove_tempfiles(self.tempfiles)

    def testHasEmptyListOfRootsInitially(self):
        self.failUnlessEqual(self.app.get_roots(), [])

    def testKeepsListOfRootsCorrectly(self):
        self.app.add_root("pink")
        self.app.add_root("pretty")
        self.failUnlessEqual(self.app.get_roots(), ["pink", "pretty"])

    def testReturnsEmptyExclusionListInitially(self):
        self.failUnlessEqual(self.app.get_exclusion_regexps(), [])

    def setup_excludes(self):
        config = self.app.get_context().config
        config.remove_option("backup", "exclude")
        config.append("backup", "exclude", "pink")
        config.append("backup", "exclude", "pretty")

    def testReturnsRightNumberOfExclusionPatterns(self):
        self.setup_excludes()
        self.failUnlessEqual(len(self.app.get_exclusion_regexps()), 2)

    def testReturnsRegexpObjects(self):
        self.setup_excludes()
        for item in self.app.get_exclusion_regexps():
            self.failUnlessEqual(type(item), type(re.compile(".")))

    def testPrunesMatchingFilenames(self):
        self.setup_excludes()
        dirname = "/dir"
        dirnames = ["subdir1", "subdir2"]
        filenames = ["filename", "pink", "file-is-pretty-indeed"]
        self.app.prune(dirname, dirnames, filenames)
        self.failUnlessEqual(filenames, ["filename"])

    def testPrunesMatchingFilenames(self):
        self.setup_excludes()
        dirname = "/dir"
        dirnames = ["subdir", "pink, dir-is-pretty-indeed"]
        filenames = ["filename1", "filename2"]
        self.app.prune(dirname, dirnames, filenames)
        self.failUnlessEqual(dirnames, ["subdir"])

    def testMakesNoFileGroupsForEmptyListOfFiles(self):
        self.failUnlessEqual(self.app.make_filegroups([]), [])

    def testMakesOneFileGroupForOneFile(self):
        filenames = self.tempfiles[:1]
        self.failUnlessEqual(len(self.app.make_filegroups(filenames)), 1)

    def testMakesOneFileGroupForMaxFilesPerGroup(self):
        filenames = self.tempfiles[:obnam.app.MAX_PER_FILEGROUP]
        self.failUnlessEqual(len(self.app.make_filegroups(filenames)), 1)

    def testMakesTwoFileGroupsForMaxFilesPerGroupPlusOne(self):
        filenames = self.tempfiles[:obnam.app.MAX_PER_FILEGROUP + 1]
        self.failUnlessEqual(len(self.app.make_filegroups(filenames)), 2)

    def testFindsFileInfoInFilelistFromPreviousGeneration(self):
        stat = obnam.utils.make_stat_result()
        fc = obnam.filelist.create_file_component_from_stat("pink", stat,
                                                            "contref",
                                                            "sigref",
                                                            "deltaref")
        filelist = obnam.filelist.Filelist()
        filelist.add_file_component("pink", fc)
        self.app.set_prevgen_filelist(filelist)
        self.failUnlessEqual(self.app.find_file_by_name("pink"),
                             (stat, "contref", "sigref", "deltaref"))

    def testFindsNoFileInfoInFilelistForNonexistingFile(self):
        filelist = obnam.filelist.Filelist()
        self.app.set_prevgen_filelist(filelist)
        self.failUnlessEqual(self.app.find_file_by_name("pink"), None)
