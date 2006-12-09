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


"""Unit tests for obnam.format."""


import stat
import unittest


import obnam


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
            self.failUnlessEqual(obnam.format.permissions(mode), correct)


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
            self.failUnlessEqual(obnam.format.filetype(mode), correct)


class FormatFileModeTest(unittest.TestCase):

    def test(self):
        self.failUnlessEqual(obnam.format.filemode(0100777), "-rwxrwxrwx")


class FormatInodeFieldsTest(unittest.TestCase):

    def test(self):
        int_fields = (obnam.cmp.ST_MODE,
                      obnam.cmp.ST_INO,
                      obnam.cmp.ST_DEV,
                      obnam.cmp.ST_NLINK,
                      obnam.cmp.ST_UID,
                      obnam.cmp.ST_GID,
                      obnam.cmp.ST_SIZE,
                      obnam.cmp.ST_ATIME,
                      obnam.cmp.ST_MTIME,
                      obnam.cmp.ST_CTIME,
                      obnam.cmp.ST_BLOCKS,
                      obnam.cmp.ST_BLKSIZE,
                      obnam.cmp.ST_RDEV)
        list = [obnam.cmp.create(x, obnam.varint.encode(1))
                for x in int_fields]
        inode = obnam.cmp.create(obnam.cmp.FILE, list)

        list = obnam.format.inode_fields(inode)
        
        self.failUnlessEqual(list, ["?--------x"] + ["1"] * 4 +
                                   ["1970-01-01 00:00:01"])
