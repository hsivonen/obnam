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
import socket
import tempfile
import unittest

import obnam


class ApplicationTests(unittest.TestCase):

    def setUp(self):
        context = obnam.context.Context()
        self.app = obnam.Application(context)

    def testHasNoHostBlockInitially(self):
        self.failUnlessEqual(self.app.get_host(), None)

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


class ApplicationLoadHostBlockTests(unittest.TestCase):

    def setUp(self):
        context = obnam.context.Context()
        cache = obnam.cache.Cache(context.config)
        context.be = obnam.backend.init(context.config, context.cache)
        self.app = obnam.Application(context)

    def testCreatesNewHostBlockWhenNoneExists(self):
        host = self.app.load_host()
        self.failUnlessEqual(host.get_id(), socket.gethostname())
        self.failUnlessEqual(host.get_generation_ids(), [])
        self.failUnlessEqual(host.get_map_block_ids(), [])
        self.failUnlessEqual(host.get_contmap_block_ids(), [])

    def testLoadsActualHostBlockWhenOneExists(self):
        context = obnam.context.Context()
        cache = obnam.cache.Cache(context.config)
        context.be = obnam.backend.init(context.config, context.cache)
        host_id = context.config.get("backup", "host-id")
        temp = obnam.obj.HostBlockObject(host_id=host_id,
                                         gen_ids=["pink", "pretty"])
        obnam.io.upload_host_block(context, temp.encode())
        
        host = self.app.load_host()
        self.failUnlessEqual(host.get_generation_ids(), ["pink", "pretty"])


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

    def testUsesJustBasenames(self):
        list = self.app.make_filegroups(self.tempfiles[:1])
        fg = list[0]
        self.failIf("/" in fg.get_names()[0])


class ApplicationUnchangedFileRecognitionTests(unittest.TestCase):

    def setUp(self):
        context = obnam.context.Context()
        self.app = obnam.Application(context)

    def testSameFileWhenStatIsIdentical(self):
        st = obnam.utils.make_stat_result()
        self.failUnless(self.app.file_is_unchanged(st, st))

    def testSameFileWhenIrrelevantFieldsChange(self):
        st1 = obnam.utils.make_stat_result()
        st2 = obnam.utils.make_stat_result(st_ino=42,
                                           st_atime=42,
                                           st_blocks=42,
                                           st_blksize=42,
                                           st_rdev=42)
        self.failUnless(self.app.file_is_unchanged(st1, st2))

    def testChangedFileWhenDevChanges(self):
        st1 = obnam.utils.make_stat_result()
        st2 = obnam.utils.make_stat_result(st_dev=42)
        self.failIf(self.app.file_is_unchanged(st1, st2))

    def testChangedFileWhenModeChanges(self):
        st1 = obnam.utils.make_stat_result()
        st2 = obnam.utils.make_stat_result(st_mode=42)
        self.failIf(self.app.file_is_unchanged(st1, st2))

    def testChangedFileWhenNlinkChanges(self):
        st1 = obnam.utils.make_stat_result()
        st2 = obnam.utils.make_stat_result(st_nlink=42)
        self.failIf(self.app.file_is_unchanged(st1, st2))

    def testChangedFileWhenUidChanges(self):
        st1 = obnam.utils.make_stat_result()
        st2 = obnam.utils.make_stat_result(st_uid=42)
        self.failIf(self.app.file_is_unchanged(st1, st2))

    def testChangedFileWhenGidChanges(self):
        st1 = obnam.utils.make_stat_result()
        st2 = obnam.utils.make_stat_result(st_gid=42)
        self.failIf(self.app.file_is_unchanged(st1, st2))

    def testChangedFileWhenSizeChanges(self):
        st1 = obnam.utils.make_stat_result()
        st2 = obnam.utils.make_stat_result(st_size=42)
        self.failIf(self.app.file_is_unchanged(st1, st2))

    def testChangedFileWhenMtimeChanges(self):
        st1 = obnam.utils.make_stat_result()
        st2 = obnam.utils.make_stat_result(st_mtime=42)
        self.failIf(self.app.file_is_unchanged(st1, st2))


class ApplicationUnchangedFileGroupTests(unittest.TestCase):

    def setUp(self):
        context = obnam.context.Context()
        self.app = obnam.Application(context)
        self.stats = {
            "pink": obnam.utils.make_stat_result(st_mtime=42),
            "pretty": obnam.utils.make_stat_result(st_mtime=105),
        }

    def mock_stat(self, filename):
        return self.stats[filename]

    def mock_filegroup(self, filenames):
        fg = obnam.obj.FileGroupObject(id=obnam.obj.object_id_new())
        for filename in filenames:
            st = self.mock_stat(filename)
            fg.add_file(filename, st, None, None, None)
        return fg

    def testSameFileGroupWhenAllFilesAreIdentical(self):
        filenames = ["pink", "pretty"]
        fg = self.mock_filegroup(filenames)
        self.failUnless(self.app.filegroup_is_unchanged(fg, filenames,
                                                        stat=self.mock_stat))

    def testChangedFileGroupWhenFileHasChanged(self):
        filenames = ["pink", "pretty"]
        fg = self.mock_filegroup(filenames)
        self.stats["pink"] = obnam.utils.make_stat_result(st_mtime=1)
        self.failIf(self.app.filegroup_is_unchanged(fg, filenames,
                                                        stat=self.mock_stat))

    def testChangedFileGroupWhenFileHasBeenRemoved(self):
        filenames = ["pink", "pretty"]
        fg = self.mock_filegroup(filenames)
        self.failIf(self.app.filegroup_is_unchanged(fg, filenames[:1],
                                                        stat=self.mock_stat))


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

    def testRaisesErrorForNonDirectory(self):
        self.failUnlessRaises(obnam.ObnamException,
                              self.app.backup_one_root,
                              self.abs("file0"))

    def testReturnsDirObject(self):
        ret = self.app.backup_one_root(self.dirname)
        self.failUnless(isinstance(ret, obnam.obj.DirObject))

    def testWalksToTheRightDirectories(self):
        self.app.backup_one_root(self.dirname)
        self.failUnlessEqual(self.dirs_walked, list(reversed(self.dirs)))

    def testFindsTheRightSubdirs(self):
        self.app.backup_one_root(self.dirname)
        self.failUnlessEqual(self.subdirs_walked, self.find_subdirs())


class ApplicationBackupTests(unittest.TestCase):

    _tree = (
        "file0",
        "pink/",
        "pink/file1",
        "pink/dir1/",
        "pink/dir1/dir2/",
        "pink/dir1/dir2/file2",
        "pretty/",
    )

    def abs(self, relative_name):
        return os.path.join(self.dirname, relative_name)

    def mktree(self, tree):
        for name in tree:
            if name.endswith("/"):
                name = self.abs(name[:-1])
                os.mkdir(name)
            else:
                name = self.abs(name)
                file(name, "w").close()

    def mock_backup_one_root(self, root):
        self.roots_backed_up.append(root)
        return self.real_backup_one_root(root)

    def setUp(self):
        self.dirname = tempfile.mkdtemp()
        self.mktree(self._tree)
        self.roots_backed_up = []
        context = obnam.context.Context()
        self.app = obnam.Application(context)
        self.real_backup_one_root = self.app.backup_one_root
        self.app.backup_one_root = self.mock_backup_one_root

    def testCallsBackupOneRootForEachRoot(self):
        dirs = [self.abs(x) for x in ["pink", "pretty"]]
        self.app.backup(dirs)
        self.failUnlessEqual(self.roots_backed_up, dirs)

    def testReturnsGenerationObject(self):
        ret = self.app.backup([self.abs("pink"), self.abs("pretty")])
        self.failUnless(isinstance(ret, obnam.obj.GenerationObject))

    def testReturnsGenerationWithTheRightRootObjects(self):
        gen = self.app.backup([self.abs("pink"), self.abs("pretty")])
        self.failUnlessEqual(len(gen.get_dirrefs()), 2)

    def testReturnsGenerationWithTimeStamps(self):
        gen = self.app.backup([self.abs("pink"), self.abs("pretty")])
        self.failIfEqual(gen.get_start_time(), None)
        self.failIfEqual(gen.get_end_time(), None)


class ApplicationMapTests(unittest.TestCase):

    def setUp(self):
        # First, set up two mappings.

        context = obnam.context.Context()
        context.cache = obnam.cache.Cache(context.config)
        context.be = obnam.backend.init(context.config, context.cache)

        obnam.map.add(context.map, "pink", "pretty")
        obnam.map.add(context.contmap, "black", "beautiful")

        map_id = context.be.generate_block_id()
        map_block = obnam.map.encode_new_to_block(context.map, map_id)
        context.be.upload_block(map_id, map_block, True)

        contmap_id = context.be.generate_block_id()
        contmap_block = obnam.map.encode_new_to_block(context.contmap, 
                                                      contmap_id)
        context.be.upload_block(contmap_id, contmap_block, True)

        host_id = context.config.get("backup", "host-id")
        host = obnam.obj.HostBlockObject(host_id=host_id,
                                         map_block_ids=[map_id],
                                         contmap_block_ids=[contmap_id])
        obnam.io.upload_host_block(context, host.encode())

        # Then set up the real context and app.

        self.context = obnam.context.Context()
        self.context.cache = obnam.cache.Cache(self.context.config)
        self.context.be = obnam.backend.init(self.context.config, 
                                             self.context.cache)
        self.app = obnam.Application(self.context)
        self.app.load_host()

    def testHasNoMapsLoadedByDefault(self):
        self.failUnlessEqual(obnam.map.count(self.context.map), 0)

    def testHasNoContentMapsLoadedByDefault(self):
        self.failUnlessEqual(obnam.map.count(self.context.contmap), 0)

    def testLoadsMapsWhenRequested(self):
        self.app.load_maps()
        self.failUnlessEqual(obnam.map.count(self.context.map), 1)

    def testLoadsContentMapsWhenRequested(self):
        self.app.load_content_maps()
        self.failUnlessEqual(obnam.map.count(self.context.contmap), 1)

    def testAddsNoNewMapsWhenNothingHasChanged(self):
        self.app.update_maps()
        self.failUnlessEqual(obnam.map.count(self.context.map), 0)

    def testAddsANewMapsWhenSomethingHasChanged(self):
        obnam.map.add(self.context.map, "pink", "pretty")
        self.app.update_maps()
        self.failUnlessEqual(obnam.map.count(self.context.map), 1)

    def testAddsNoNewContentMapsWhenNothingHasChanged(self):
        self.app.update_content_maps()
        self.failUnlessEqual(obnam.map.count(self.context.contmap), 0)

    def testAddsANewContentMapsWhenSomethingHasChanged(self):
        obnam.map.add(self.context.contmap, "pink", "pretty")
        self.app.update_content_maps()
        self.failUnlessEqual(obnam.map.count(self.context.contmap), 1)


class ApplicationFinishTests(unittest.TestCase):

    def testRemovesHostObject(self):
        self.context = obnam.context.Context()
        self.context.cache = obnam.cache.Cache(self.context.config)
        self.context.be = obnam.backend.init(self.context.config, 
                                             self.context.cache)
        self.app = obnam.Application(self.context)
        self.app.load_host()

        self.app.finish([])
        self.failUnlessEqual(self.app.get_host(), None)
