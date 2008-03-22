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


"""Unit tests for app.py."""


import os
import re
import shutil
import tempfile
import unittest

import obnam


class ApplicationTests(unittest.TestCase):

    def setUp(self):
        context = obnam.context.Context()
        self.app = obnam.Application(context)

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


class ApplicationMakeFileGroupsTests(unittest.TestCase):

    def make_tempfiles(self, n):
        list = []
        for i in range(n):
            fd, name = tempfile.mkstemp(dir=self.tempdir)
            os.close(fd)
            if (i % 2) == 0:
                os.remove(name)
                os.mkfifo(name)
            list.append(name)
        return list

    def setUp(self):
        context = obnam.context.Context()
        self.app = obnam.Application(context)
        
        self.tempdir = tempfile.mkdtemp()
        self.tempfiles = self.make_tempfiles(obnam.app.MAX_PER_FILEGROUP + 1)
        
    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def testReturnsNoFileGroupsForEmptyListOfFiles(self):
        self.failUnlessEqual(self.app.make_filegroups([]), [])

    def testReturnsOneFileGroupForOneFile(self):
        filenames = self.tempfiles[:1]
        self.failUnlessEqual(len(self.app.make_filegroups(filenames)), 1)

    def testReturnsOneFileGroupForMaxFilesPerGroup(self):
        filenames = self.tempfiles[:obnam.app.MAX_PER_FILEGROUP]
        self.failUnlessEqual(len(self.app.make_filegroups(filenames)), 1)

    def testReturnsTwoFileGroupsForMaxFilesPerGroupPlusOne(self):
        filenames = self.tempfiles[:obnam.app.MAX_PER_FILEGROUP + 1]
        self.failUnlessEqual(len(self.app.make_filegroups(filenames)), 2)


class ApplicationFindFileByNameTests(unittest.TestCase):

    def setUp(self):
        context = obnam.context.Context()
        self.app = obnam.Application(context)

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


class ApplicationBackupsOneDirectoryTests(unittest.TestCase):

    def abs(self, relative_name):
        return os.path.join(self.dirname, relative_name)

    def make_file(self, name):
        file(self.abs(name), "w").close()

    def make_dirobject(self, relative_name):
        return obnam.obj.DirObject(id=obnam.obj.object_id_new(),
                                   name=self.abs(relative_name))

    def setUp(self):
        context = obnam.context.Context()
        self.app = obnam.Application(context)
        self.dirname = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.dirname)

    def testWithCorrectName(self):
        dir = self.app.backup_one_dir(self.dirname, [], [])
        self.failUnlessEqual(dir.get_name(), os.path.basename(self.dirname))

    def testWithCorrectStat(self):
        dir = self.app.backup_one_dir(self.dirname, [], [])
        self.failUnlessEqual(dir.get_stat(), os.stat(self.dirname))

    def testWithCorrectNumberOfDirrefsWhenThereAreNoneGiven(self):
        dir = self.app.backup_one_dir(self.dirname, [], [])
        self.failUnlessEqual(dir.get_dirrefs(), [])

    def testWithCorrectNumberOfFilegrouprefsWhenThereAreNoneGiven(self):
        dir = self.app.backup_one_dir(self.dirname, [], [])
        self.failUnlessEqual(dir.get_filegrouprefs(), [])

    def _filegroups(self, file_count):
        max = obnam.app.MAX_PER_FILEGROUP
        return (file_count + max - 1) / max

    def testWithCorrectNumberOfFilegrouprefsWhenSomeAreGiven(self):
        self.make_file("pink")
        self.make_file("pretty")
        files = os.listdir(self.dirname)
        files = [name for name in files if os.path.isfile(self.abs(name))]
        dir = self.app.backup_one_dir(self.dirname, [], files)
        self.failUnlessEqual(len(dir.get_filegrouprefs()), 
                                 self._filegroups(len(files)))


    def testWithCorrectNumberOfDirrefsWhenSomeAreGiven(self):
        os.mkdir(self.abs("pink"))
        os.mkdir(self.abs("pretty"))
        subdirs = [self.make_dirobject(_) for _ in ["pink", "pretty"]]
        dir = self.app.backup_one_dir(self.dirname, subdirs, [])
        self.failUnlessEqual(len(dir.get_dirrefs()), 2)


class ApplicationBackupOneRootTests(unittest.TestCase):

    _tree = (
        "file0",
        "pink/",
        "pink/file1",
        "pink/dir1/",
        "pink/dir1/dir2/",
        "pink/dir1/dir2/file2",
    )

    def abs(self, relative_name):
        return os.path.join(self.dirname, relative_name)

    def mktree(self, tree):
        for name in tree:
            if name.endswith("/"):
                name = self.abs(name[:-1])
                self.dirs.append(name)
                os.mkdir(name)
            else:
                name = self.abs(name)
                self.files.append(name)
                file(name, "w").close()

    def mock_backup_one_dir(self, dirname, subdirs, filenames):
        self.dirs_walked.append(dirname)
        assert dirname not in self.subdirs_walked
        self.subdirs_walked[dirname] = [os.path.join(dirname, x.get_name())
                                        for x in subdirs]
        return self.real_backup_one_dir(dirname, subdirs, filenames)

    def find_subdirs(self):
        dict = {}
        for dirname, dirnames, filenames in os.walk(self.dirname):
            dict[dirname] = [os.path.join(dirname, _) for _ in dirnames]
        return dict

    def setUp(self):
        context = obnam.context.Context()
        self.app = obnam.Application(context)
        self.real_backup_one_dir = self.app.backup_one_dir
        self.app.backup_one_dir = self.mock_backup_one_dir
        self.dirs_walked = []
        self.subdirs_walked = {}
        self.dirname = tempfile.mkdtemp()
        self.dirs = [self.dirname]
        self.files = []
        self.mktree(self._tree)

    def tearDown(self):
        shutil.rmtree(self.dirname)

    def testWalksToTheRightDirectories(self):
        self.app.backup_one_root(self.dirname)
        self.failUnlessEqual(self.dirs_walked, list(reversed(self.dirs)))

    def testFindsTheRightSubdirs(self):
        self.app.backup_one_root(self.dirname)
        self.failUnlessEqual(self.subdirs_walked, self.find_subdirs())


class ApplicationMakeBackupTests(unittest.TestCase):

    def mock_backup_one_root(self, root):
        self.roots_backed_up.append(root)

    def testCallsBackupOneRootForEachRoot(self):
        self.roots_backed_up = []
        context = obnam.context.Context()
        app = obnam.Application(context)
        app.backup_one_root = self.mock_backup_one_root
        app.add_root("/pink")
        app.add_root("/pretty")
        app.backup()
        self.failUnlessEqual(self.roots_backed_up, ["/pink", "/pretty"])
