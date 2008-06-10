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


"""Unit tests for obnamlib.format."""


import re
import stat
import StringIO
import unittest


import obnamlib


class Fake:

    pass


class FormatPermissionsTests(unittest.TestCase):

    def testFormatPermissions(self):
        facit = (
            (00000, "---------"),   # No permissions for anyone
            (00100, "--x------"),   # Execute for owner
            (00200, "-w-------"),   # Write for owner
            (00400, "r--------"),   # Read for owner
            (00010, "-----x---"),   # Execute for group
            (00020, "----w----"),   # Write for group
            (00040, "---r-----"),   # Read for group
            (00001, "--------x"),   # Execute for others
            (00002, "-------w-"),   # Write for others
            (00004, "------r--"),   # Read for others
            (01001, "--------t"),   # Sticky bit
            (01000, "--------T"),   # Sticky bit (upper case since no x)
            (02010, "-----s---"),   # Set group id
            (02000, "-----S---"),   # Set group id (upper case since no x)
            (04100, "--s------"),   # Set user id
            (04000, "--S------"),   # Set user id (upper case since no x)
        )
        for mode, correct in facit:
            self.failUnlessEqual(obnamlib.format.permissions(mode), correct)


class FormatFileTypeTests(unittest.TestCase):

    def test(self):
        facit = (
            (0, "?"), # Unknown
            (stat.S_IFSOCK, "s"),   # socket
            (stat.S_IFLNK, "l"),    # symbolic link
            (stat.S_IFREG, "-"),    # regular file
            (stat.S_IFBLK, "b"),    # block device
            (stat.S_IFDIR, "d"),    # directory
            (stat.S_IFCHR, "c"),    # character device
            (stat.S_IFIFO, "p"),    # FIFO
        )
        for mode, correct in facit:
            self.failUnlessEqual(obnamlib.format.filetype(mode), correct)


class FormatFileModeTest(unittest.TestCase):

    def test(self):
        self.failUnlessEqual(obnamlib.format.filemode(0100777), "-rwxrwxrwx")


class FormatInodeFieldsTest(unittest.TestCase):

    def test(self):
        st = Fake()
        st.st_mode = 1
        st.st_ino = 1
        st.st_dev = 1
        st.st_nlink = 1
        st.st_uid = 1
        st.st_gid = 1
        st.st_size = 1
        st.st_atime = 1
        st.st_mtime = 1
        st.st_ctime = 1
        st.st_blocks = 1
        st.st_blksize = 1
        st.st_rdev = 1
        file_component = \
            obnamlib.filelist.create_file_component_from_stat("Makefile", st, 
                                                           None, None, None)

        list = obnamlib.format.inode_fields(file_component)
        
        self.failUnlessEqual(list, ["?--------x"] + ["1"] * 4 +
                                   ["1970-01-01 00:00:01"])


class FormatTimeTests(unittest.TestCase):

    def test(self):
        self.failUnlessEqual(obnamlib.format.timestamp(1), "1970-01-01 00:00:01")



class ListingTests(unittest.TestCase):

    dirpat = re.compile(r"^drwxrwxrwx 0 0 0 0 1970-01-01 00:00:00 pretty$")
    filepat = re.compile(r"^-rw-rw-rw- 0 0 0 0 1970-01-01 00:00:00 pink$")

    def make_filegroup(self, filenames):
        fg = obnamlib.obj.FileGroupObject(id=obnamlib.obj.object_id_new())
        mode = 0666 | stat.S_IFREG
        st = obnamlib.utils.make_stat_result(st_mode=mode)
        for filename in filenames:
            fg.add_file(filename, st, None, None, None)

        self.objects[fg.get_id()] = fg
        return fg

    def make_dir(self, name, dirs, filegroups):
        mode = 0777 | stat.S_IFDIR
        st = obnamlib.utils.make_stat_result(st_mode=mode)
        dir = obnamlib.obj.DirObject(id=obnamlib.obj.object_id_new(),
                                  name=name,
                                  stat=st,
                                  dirrefs=[x.get_id() for x in dirs],
                                  filegrouprefs=[x.get_id() 
                                                 for x in filegroups])
        self.objects[dir.get_id()] = dir
        return dir

    def mock_get_object(self, context, objid):
        return self.objects.get(objid)

    def setUp(self):
        self.objects = {}
        self.file = StringIO.StringIO()
        self.listing = obnamlib.format.Listing(None, self.file)
        self.listing._get_object = self.mock_get_object

    def testWritesNothingForNothing(self):
        self.listing.walk([], [])
        self.failUnlessEqual(self.file.getvalue(), "")

    def testWritesAFileLineForOneFile(self):
        fg = self.make_filegroup(["pink"])
        self.listing.walk([], [fg])
        self.failUnless(self.filepat.match(self.file.getvalue()))

    def testWritesADirLineForOneDir(self):
        dir = self.make_dir("pretty", [], [])
        self.listing.walk([dir], [])
        self.failUnless(self.dirpat.match(self.file.getvalue()))

    def testWritesFileInSubdirectoryCorrectly(self):
        fg = self.make_filegroup(["pink"])
        dir = self.make_dir("pretty", [], [fg])
        self.listing.walk([dir], [])
        s = self.file.getvalue()
        lines = s.splitlines()
        self.failUnlessEqual(len(lines), 4)
        self.failUnless(self.dirpat.match(lines[0]))
        self.failUnlessEqual(lines[1], "")
        self.failUnlessEqual(lines[2], "pretty:")
        self.failUnless(self.filepat.match(lines[3]))
