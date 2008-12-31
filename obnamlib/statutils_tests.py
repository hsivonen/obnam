# obnamlib/__init__.py
#
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


import unittest

import obnamlib


class StatTests(unittest.TestCase):

    def test_encodes_and_decodes_stat_component_correctly(self):
        stat = obnamlib.make_stat(st_mode=1, st_ino=2)
        encoded = obnamlib.encode_stat(stat)
        decoded = obnamlib.decode_stat(encoded)
        self.assertEqual(stat, decoded)

    def testSetsEverytingToZeroByDefault(self):
        st = obnamlib.make_stat()
        self.failUnlessEqual(st.st_mode, 0)
        self.failUnlessEqual(st.st_ino, 0)
        self.failUnlessEqual(st.st_dev, 0)
        self.failUnlessEqual(st.st_nlink, 0)
        self.failUnlessEqual(st.st_uid, 0)
        self.failUnlessEqual(st.st_gid, 0)
        self.failUnlessEqual(st.st_size, 0)
        self.failUnlessEqual(st.st_atime, 0)
        self.failUnlessEqual(st.st_mtime, 0)
        self.failUnlessEqual(st.st_ctime, 0)
        self.failUnlessEqual(st.st_blocks, 0)
        self.failUnlessEqual(st.st_blksize, 0)
        self.failUnlessEqual(st.st_rdev, 0)

    def testSetsDesiredFieldToDesiredValue(self):
        st = obnamlib.make_stat(st_size=12765)
        self.failUnlessEqual(st.st_size, 12765)
