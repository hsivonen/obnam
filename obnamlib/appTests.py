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

import obnamlib


class ApplicationTests(unittest.TestCase):

    def setUp(self):
        context = obnamlib.context.Context()
        self.app = obnamlib.Application(context)

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

    def testSetsPreviousGenerationToNoneInitially(self):
        self.failUnlessEqual(self.app.get_previous_generation(), None)

    def testSetsPreviousGenerationCorrectly(self):
        self.app.set_previous_generation("pink")
        self.failUnlessEqual(self.app.get_previous_generation(), "pink")


class ApplicationLoadHostBlockTests(unittest.TestCase):

    def setUp(self):
        context = obnamlib.context.Context()
        cache = obnamlib.Cache(context.config)
        context.be = obnamlib.backend.init(context.config, context.cache)
        self.app = obnamlib.Application(context)

    def tearDown(self):
        for x in ["cache", "store"]:
            dirname = self.app._context.config.get("backup", x)
            if os.path.isdir(dirname):
                shutil.rmtree(dirname)

    def testCreatesNewHostBlockWhenNoneExists(self):
        host = self.app.load_host()
        self.failUnlessEqual(host.get_id(), socket.gethostname())
        self.failUnlessEqual(host.get_generation_ids(), [])
        self.failUnlessEqual(host.get_map_block_ids(), [])
        self.failUnlessEqual(host.get_contmap_block_ids(), [])

    def testLoadsActualHostBlockWhenOneExists(self):
        context = obnamlib.context.Context()
        cache = obnamlib.Cache(context.config)
        context.be = obnamlib.backend.init(context.config, context.cache)
        host_id = context.config.get("backup", "host-id")
        temp = obnamlib.obj.HostBlockObject(host_id=host_id,
                                         gen_ids=["pink", "pretty"])
        obnamlib.io.upload_host_block(context, temp.encode())
        
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
        context = obnamlib.context.Context()
        self.app = obnamlib.Application(context)
        
        self.tempdir = tempfile.mkdtemp()
        self.tempfiles = self.make_tempfiles(obnamlib.app.MAX_PER_FILEGROUP + 1)
        
    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def testReturnsNoFileGroupsForEmptyListOfFiles(self):
        self.failUnlessEqual(self.app.make_filegroups([]), [])

    def testReturnsOneFileGroupForOneFile(self):
        filenames = self.tempfiles[:1]
        self.failUnlessEqual(len(self.app.make_filegroups(filenames)), 1)

    def testReturnsOneFileGroupForMaxFilesPerGroup(self):
        filenames = self.tempfiles[:obnamlib.app.MAX_PER_FILEGROUP]
        self.failUnlessEqual(len(self.app.make_filegroups(filenames)), 1)

    def testReturnsTwoFileGroupsForMaxFilesPerGroupPlusOne(self):
        filenames = self.tempfiles[:obnamlib.app.MAX_PER_FILEGROUP + 1]
        self.failUnlessEqual(len(self.app.make_filegroups(filenames)), 2)

    def testUsesJustBasenames(self):
        list = self.app.make_filegroups(self.tempfiles[:1])
        fg = list[0]
        self.failIf("/" in fg.get_names()[0])


class ApplicationUnchangedFileRecognitionTests(unittest.TestCase):

    def setUp(self):
        context = obnamlib.context.Context()
        self.app = obnamlib.Application(context)

    def testSameFileWhenStatIsIdentical(self):
        st = obnamlib.utils.make_stat_result()
        self.failUnless(self.app.file_is_unchanged(st, st))

    def testSameFileWhenIrrelevantFieldsChange(self):
        st1 = obnamlib.utils.make_stat_result()
        st2 = obnamlib.utils.make_stat_result(st_ino=42,
                                           st_atime=42,
                                           st_blocks=42,
                                           st_blksize=42,
                                           st_rdev=42)
        self.failUnless(self.app.file_is_unchanged(st1, st2))

    def testChangedFileWhenDevChanges(self):
        st1 = obnamlib.utils.make_stat_result()
        st2 = obnamlib.utils.make_stat_result(st_dev=42)
        self.failIf(self.app.file_is_unchanged(st1, st2))

    def testChangedFileWhenModeChanges(self):
        st1 = obnamlib.utils.make_stat_result()
        st2 = obnamlib.utils.make_stat_result(st_mode=42)
        self.failIf(self.app.file_is_unchanged(st1, st2))

    def testChangedFileWhenNlinkChanges(self):
        st1 = obnamlib.utils.make_stat_result()
        st2 = obnamlib.utils.make_stat_result(st_nlink=42)
        self.failIf(self.app.file_is_unchanged(st1, st2))

    def testChangedFileWhenUidChanges(self):
        st1 = obnamlib.utils.make_stat_result()
        st2 = obnamlib.utils.make_stat_result(st_uid=42)
        self.failIf(self.app.file_is_unchanged(st1, st2))

    def testChangedFileWhenGidChanges(self):
        st1 = obnamlib.utils.make_stat_result()
        st2 = obnamlib.utils.make_stat_result(st_gid=42)
        self.failIf(self.app.file_is_unchanged(st1, st2))

    def testChangedFileWhenSizeChanges(self):
        st1 = obnamlib.utils.make_stat_result()
        st2 = obnamlib.utils.make_stat_result(st_size=42)
        self.failIf(self.app.file_is_unchanged(st1, st2))

    def testChangedFileWhenMtimeChanges(self):
        st1 = obnamlib.utils.make_stat_result()
        st2 = obnamlib.utils.make_stat_result(st_mtime=42)
        self.failIf(self.app.file_is_unchanged(st1, st2))


class ApplicationUnchangedFileGroupTests(unittest.TestCase):

    def setUp(self):
        context = obnamlib.context.Context()
        self.app = obnamlib.Application(context)
        self.dir = "dirname"
        self.stats = {
            "dirname/pink": obnamlib.utils.make_stat_result(st_mtime=42),
            "dirname/pretty": obnamlib.utils.make_stat_result(st_mtime=105),
        }

    def mock_stat(self, filename):
        self.failUnless(filename.startswith(self.dir))
        return self.stats[filename]

    def mock_filegroup(self, filenames):
        fg = obnamlib.obj.FileGroupObject(id=obnamlib.obj.object_id_new())
        for filename in filenames:
            st = self.mock_stat(os.path.join(self.dir, filename))
            fg.add_file(filename, st, None, None, None)
        return fg

    def testSameFileGroupWhenAllFilesAreIdentical(self):
        filenames = ["pink", "pretty"]
        fg = self.mock_filegroup(filenames)
        self.failUnless(self.app.filegroup_is_unchanged(self.dir, fg, 
                                                        filenames,
                                                        stat=self.mock_stat))

    def testChangedFileGroupWhenFileHasChanged(self):
        filenames = ["pink", "pretty"]
        fg = self.mock_filegroup(filenames)
        self.stats["dirname/pink"] = obnamlib.utils.make_stat_result(st_mtime=1)
        self.failIf(self.app.filegroup_is_unchanged(self.dir, fg, filenames,
                                                    stat=self.mock_stat))

    def testChangedFileGroupWhenFileHasBeenRemoved(self):
        filenames = ["pink", "pretty"]
        fg = self.mock_filegroup(filenames)
        self.failIf(self.app.filegroup_is_unchanged(self.dir, fg, 
                                                    filenames[:1],
                                                    stat=self.mock_stat))


class ApplicationUnchangedDirTests(unittest.TestCase):

    def setUp(self):
        context = obnamlib.context.Context()
        self.app = obnamlib.Application(context)

    def make_dir(self, name, dirrefs, filegrouprefs, stat=None):
        if stat is None:
            stat = obnamlib.utils.make_stat_result()
        return obnamlib.obj.DirObject(id=obnamlib.obj.object_id_new(),
                                   name=name,
                                   stat=stat,
                                   dirrefs=dirrefs,
                                   filegrouprefs=filegrouprefs)

    def testSameDirWhenNothingHasChanged(self):
        dir = self.make_dir("name", [], ["pink", "pretty"])
        self.failUnless(self.app.dir_is_unchanged(dir, dir))

    def testChangedDirWhenFileGroupHasBeenRemoved(self):
        dir1 = self.make_dir("name", [], ["pink", "pretty"])
        dir2 = self.make_dir("name", [], ["pink"])
        self.failIf(self.app.dir_is_unchanged(dir1, dir2))

    def testChangedDirWhenFileGroupHasBeenAdded(self):
        dir1 = self.make_dir("name", [], ["pink"])
        dir2 = self.make_dir("name", [], ["pink", "pretty"])
        self.failIf(self.app.dir_is_unchanged(dir1, dir2))

    def testChangedDirWhenDirHasBeenRemoved(self):
        dir1 = self.make_dir("name", ["pink", "pretty"], [])
        dir2 = self.make_dir("name", ["pink"], [])
        self.failIf(self.app.dir_is_unchanged(dir1, dir2))

    def testChangedDirWhenDirHasBeenAdded(self):
        dir1 = self.make_dir("name", ["pink"], [])
        dir2 = self.make_dir("name", ["pink", "pretty"], [])
        self.failIf(self.app.dir_is_unchanged(dir1, dir2))

    def testChangedDirWhenNameHasChanged(self):
        dir1 = self.make_dir("name1", [], [])
        dir2 = self.make_dir("name2", [], [])
        self.failIf(self.app.dir_is_unchanged(dir1, dir2))

    def testSameDirWhenIrrelevantStatFieldsHaveChanged(self):
        stat = obnamlib.utils.make_stat_result(st_ino=42,
                                            st_atime=42,
                                            st_blocks=42,
                                            st_blksize=42,
                                            st_rdev=42)

        dir1 = self.make_dir("name", [], [])
        dir2 = self.make_dir("name", [], [], stat=stat)
        self.failUnless(self.app.dir_is_unchanged(dir1, dir2))

    def testChangedDirWhenDevHasChanged(self):
        dir1 = self.make_dir("name1", [], [])
        dir2 = self.make_dir("name2", [], [],
                             stat=obnamlib.utils.make_stat_result(st_dev=105))
        self.failIf(self.app.dir_is_unchanged(dir1, dir2))

    def testChangedDirWhenModeHasChanged(self):
        dir1 = self.make_dir("name1", [], [])
        dir2 = self.make_dir("name2", [], [],
                             stat=obnamlib.utils.make_stat_result(st_mode=105))
        self.failIf(self.app.dir_is_unchanged(dir1, dir2))

    def testChangedDirWhenNlinkHasChanged(self):
        dir1 = self.make_dir("name1", [], [])
        dir2 = self.make_dir("name2", [], [],
                             stat=obnamlib.utils.make_stat_result(st_nlink=105))
        self.failIf(self.app.dir_is_unchanged(dir1, dir2))

    def testChangedDirWhenUidHasChanged(self):
        dir1 = self.make_dir("name1", [], [])
        dir2 = self.make_dir("name2", [], [],
                             stat=obnamlib.utils.make_stat_result(st_uid=105))
        self.failIf(self.app.dir_is_unchanged(dir1, dir2))

    def testChangedDirWhenGidHasChanged(self):
        dir1 = self.make_dir("name1", [], [])
        dir2 = self.make_dir("name2", [], [],
                             stat=obnamlib.utils.make_stat_result(st_gid=105))
        self.failIf(self.app.dir_is_unchanged(dir1, dir2))

    def testChangedDirWhenSizeHasChanged(self):
        dir1 = self.make_dir("name1", [], [])
        dir2 = self.make_dir("name2", [], [],
                             stat=obnamlib.utils.make_stat_result(st_size=105))
        self.failIf(self.app.dir_is_unchanged(dir1, dir2))

    def testChangedDirWhenMtimeHasChanged(self):
        dir1 = self.make_dir("name1", [], [])
        dir2 = self.make_dir("name2", [], [],
                             stat=obnamlib.utils.make_stat_result(st_mtime=105))
        self.failIf(self.app.dir_is_unchanged(dir1, dir2))


class ApplicationFindUnchangedFilegroupsTests(unittest.TestCase):

    def setUp(self):
        context = obnamlib.context.Context()
        self.app = obnamlib.Application(context)
        self.dirname = "dirname"
        self.stats = {
            "dirname/pink": obnamlib.utils.make_stat_result(st_mtime=42),
            "dirname/pretty": obnamlib.utils.make_stat_result(st_mtime=105),
        }
        self.names = ["pink", "pretty"]
        self.pink = self.mock_filegroup(["pink"])
        self.pretty = self.mock_filegroup(["pretty"])
        self.groups = [self.pink, self.pretty]

    def mock_filegroup(self, filenames):
        fg = obnamlib.obj.FileGroupObject(id=obnamlib.obj.object_id_new())
        for filename in filenames:
            st = self.mock_stat(os.path.join(self.dirname, filename))
            fg.add_file(filename, st, None, None, None)
        return fg

    def mock_stat(self, filename):
        return self.stats[filename]

    def find(self, filegroups, filenames):
        return self.app.unchanged_groups(self.dirname, filegroups,  filenames, 
                                         stat=self.mock_stat)

    def testReturnsEmptyListForEmptyListOfGroups(self):
        self.failUnlessEqual(self.find([], self.names), [])

    def testReturnsEmptyListForEmptyListOfFilenames(self):
        self.failUnlessEqual(self.find(self.groups, []), [])

    def testReturnsPinkGroupWhenPrettyIsChanged(self):
        self.stats["dirname/pretty"] = obnamlib.utils.make_stat_result()
        self.failUnlessEqual(self.find(self.groups, self.names), [self.pink])

    def testReturnsPrettyGroupWhenPinkIsChanged(self):
        self.stats["dirname/pink"] = obnamlib.utils.make_stat_result()
        self.failUnlessEqual(self.find(self.groups, self.names), [self.pretty])

    def testReturnsPinkAndPrettyWhenBothAreUnchanged(self):
        self.failUnlessEqual(set(self.find(self.groups, self.names)),
                             set(self.groups))

    def testReturnsEmptyListWhenEverythingIsChanged(self):
        self.stats["dirname/pink"] = obnamlib.utils.make_stat_result()
        self.stats["dirname/pretty"] = obnamlib.utils.make_stat_result()
        self.failUnlessEqual(self.find(self.groups, self.names), [])


class ApplicationGetDirInPreviousGenerationTests(unittest.TestCase):

    class MockStore:
    
        def __init__(self):
            self.dict = {
                "pink": obnamlib.obj.DirObject(id="id", name="pink"),
            }
    
        def lookup_dir(self, gen, pathname):
            return self.dict.get(pathname, None)

    def setUp(self):
        context = obnamlib.context.Context()
        self.app = obnamlib.Application(context)
        self.app._store = self.MockStore()
        self.app.set_previous_generation("prevgen")

    def testReturnsNoneIfDirectoryDidNotExist(self):
        self.failUnlessEqual(self.app.get_dir_in_previous_generation("xx"),
                             None)

    def testReturnsDirObjectIfDirectoryDidExist(self):
        dir = self.app.get_dir_in_previous_generation("pink")
        self.failUnlessEqual(dir.get_name(), "pink")


class ApplicationGetFileInPreviousGenerationTests(unittest.TestCase):

    class MockStore:
    
        def __init__(self):
            self.dict = {
                "pink": obnamlib.cmp.Component(obnamlib.cmp.FILE, [])
            }
    
        def lookup_file(self, gen, pathname):
            return self.dict.get(pathname, None)

    def setUp(self):
        context = obnamlib.context.Context()
        self.app = obnamlib.Application(context)
        self.app._store = self.MockStore()
        self.app.set_previous_generation("prevgen")

    def testReturnsNoneIfPreviousGenerationIsUnset(self):
        self.app.set_previous_generation(None)
        self.failUnlessEqual(self.app.get_file_in_previous_generation("xx"),
                             None)

    def testReturnsNoneIfFileDidNotExist(self):
        self.failUnlessEqual(self.app.get_file_in_previous_generation("xx"),
                             None)

    def testReturnsFileComponentIfFileDidExist(self):
        cmp = self.app.get_file_in_previous_generation("pink")
        self.failUnlessEqual(cmp.get_kind(), obnamlib.cmp.FILE)


class ApplicationSelectFilesToBackUpTests(unittest.TestCase):

    class MockStore:
    
        def __init__(self, objs):
            self._objs = objs
    
        def get_object(self, id):
            for obj in self._objs:
                if obj.get_id() == id:
                    return obj
            return None

    def setUp(self):
        self.dirname = "dirname"
        self.stats = {
            "dirname/pink": obnamlib.utils.make_stat_result(st_mtime=42),
            "dirname/pretty": obnamlib.utils.make_stat_result(st_mtime=105),
        }
        self.names = ["pink", "pretty"]
        self.pink = self.mock_filegroup(["pink"])
        self.pretty = self.mock_filegroup(["pretty"])
        self.groups = [self.pink, self.pretty]

        self.dir = obnamlib.obj.DirObject(id="id", name=self.dirname,
                                       filegrouprefs=[x.get_id() 
                                                      for x in self.groups])

        store = self.MockStore(self.groups + [self.dir])

        context = obnamlib.context.Context()
        self.app = obnamlib.Application(context)
        self.app._store = store
        self.app.get_dir_in_previous_generation = self.mock_get_dir_in_prevgen

    def mock_get_dir_in_prevgen(self, dirname):
        if dirname == self.dirname:
            return self.dir
        else:
            return None

    def mock_filegroup(self, filenames):
        fg = obnamlib.obj.FileGroupObject(id=obnamlib.obj.object_id_new())
        for filename in filenames:
            st = self.mock_stat(os.path.join(self.dirname, filename))
            fg.add_file(filename, st, None, None, None)
        return fg

    def mock_stat(self, filename):
        return self.stats[filename]

    def select(self):
        return self.app.select_files_to_back_up(self.dirname, self.names,
                                                stat=self.mock_stat)

    def testReturnsNoOldGroupsIfDirectoryDidNotExist(self):
        self.dir = None
        self.failUnlessEqual(self.select(), ([], self.names))

    def testReturnsNoOldGroupsIfEverythingIsChanged(self):
        self.stats["dirname/pink"] = obnamlib.utils.make_stat_result()
        self.stats["dirname/pretty"] = obnamlib.utils.make_stat_result()
        self.failUnlessEqual(self.select(), ([], self.names))

    def testReturnsOneGroupAndOneFileWhenJustOneIsChanged(self):
        self.stats["dirname/pink"] = obnamlib.utils.make_stat_result()
        self.failUnlessEqual(self.select(), ([self.pretty], ["pink"]))

    def testReturnsBothGroupsWhenNothingIsChanged(self):
        self.failUnlessEqual(self.select(), (self.groups, []))


class ApplicationFindFileByNameTests(unittest.TestCase):

    def setUp(self):
        context = obnamlib.context.Context()
        self.app = obnamlib.Application(context)

    def testFindsFileInfoInFilelistFromPreviousGeneration(self):
        stat = obnamlib.utils.make_stat_result()
        fc = obnamlib.filelist.create_file_component_from_stat("pink", stat,
                                                            "contref",
                                                            "sigref",
                                                            "deltaref")
        filelist = obnamlib.filelist.Filelist()
        filelist.add_file_component("pink", fc)
        self.app.set_prevgen_filelist(filelist)
        file = self.app.find_file_by_name("pink")
        self.failUnlessEqual(
            obnamlib.cmp.parse_stat_component(
                file.first_by_kind(obnamlib.cmp.STAT)), 
            stat)
        self.failUnlessEqual(file.first_string_by_kind(obnamlib.cmp.CONTREF),
                             "contref")
        self.failUnlessEqual(file.first_string_by_kind(obnamlib.cmp.SIGREF),
                             "sigref")
        self.failUnlessEqual(file.first_string_by_kind(obnamlib.cmp.DELTAREF),
                             "deltaref")

    def testFindsNoFileInfoInFilelistForNonexistingFile(self):
        filelist = obnamlib.filelist.Filelist()
        self.app.set_prevgen_filelist(filelist)
        self.failUnlessEqual(self.app.find_file_by_name("pink"), None)


class ApplicationBackupsOneDirectoryTests(unittest.TestCase):

    def abs(self, relative_name):
        return os.path.join(self.dirname, relative_name)

    def make_file(self, name):
        file(self.abs(name), "w").close()

    def make_dirobject(self, relative_name):
        return obnamlib.obj.DirObject(id=obnamlib.obj.object_id_new(),
                                   name=self.abs(relative_name))

    def setUp(self):
        context = obnamlib.context.Context()
        self.app = obnamlib.Application(context)
        self.dirname = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.dirname)

    def testWithCorrectName(self):
        dir = self.app.backup_one_dir(self.dirname, [], [], is_root=True)
        self.failUnlessEqual(dir.get_name(), self.dirname)

    def testWithCorrectNameWhenNameEndsInSlash(self):
        dir = self.app.backup_one_dir(self.dirname + os.sep, [], [])
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
        max = obnamlib.app.MAX_PER_FILEGROUP
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

    def mock_backup_one_dir(self, dirname, subdirs, filenames, is_root=False):
        self.dirs_walked.append(dirname)
        assert dirname not in self.subdirs_walked
        self.subdirs_walked[dirname] = [os.path.join(dirname, x.get_name())
                                        for x in subdirs]
        return self.real_backup_one_dir(dirname, subdirs, filenames,
                                        is_root=is_root)

    def find_subdirs(self):
        dict = {}
        for dirname, dirnames, filenames in os.walk(self.dirname):
            dict[dirname] = [os.path.join(dirname, _) for _ in dirnames]
        return dict

    def setUp(self):
        context = obnamlib.context.Context()
        self.app = obnamlib.Application(context)
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
        self.failUnlessRaises(obnamlib.ObnamException,
                              self.app.backup_one_root,
                              self.abs("file0"))

    def testReturnsDirObject(self):
        ret = self.app.backup_one_root(self.dirname)
        self.failUnless(isinstance(ret, obnamlib.obj.DirObject))

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
        context = obnamlib.context.Context()
        self.app = obnamlib.Application(context)
        self.real_backup_one_root = self.app.backup_one_root
        self.app.backup_one_root = self.mock_backup_one_root

    def testCallsBackupOneRootForEachRoot(self):
        dirs = [self.abs(x) for x in ["pink", "pretty"]]
        for gen in self.app.backup(dirs):
            pass
        self.failUnlessEqual(self.roots_backed_up, dirs)

    def testReturnsGenerationObject(self):
        for ret in self.app.backup([self.abs("pink"), self.abs("pretty")]):
            self.failUnless(isinstance(ret, obnamlib.obj.GenerationObject))

    def testReturnsGenerationWithTheRightRootObjects(self):
        for gen in self.app.backup([self.abs("pink"), self.abs("pretty")]):
            self.failUnlessEqual(len(gen.get_dirrefs()), 2)

    def testReturnsGenerationWithTimeStamps(self):
        for gen in self.app.backup([self.abs("pink"), self.abs("pretty")]):
            self.failIfEqual(gen.get_start_time(), None)
            self.failIfEqual(gen.get_end_time(), None)
