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
import mox

import obnamlib


class BackupCommandTests(unittest.TestCase):

    def setUp(self):
        self.mox = mox.Mox()
        self.cmd = obnamlib.BackupCommand()
        self.cmd.store = self.mox.CreateMock(obnamlib.Store)
        self.cmd.fs = self.mox.CreateMock(obnamlib.VirtualFileSystem)

    def test_backs_up_new_file_correctly(self):
        f = self.mox.CreateMock(file)
        fc = self.mox.CreateMock(obnamlib.FileContents)
        fc.id = "contentsid"
        part = self.mox.CreateMock(obnamlib.FilePart)
        part.id = "partid"

        self.cmd.store.new_object(kind=obnamlib.FILECONTENTS).AndReturn(fc)
        self.cmd.fs.open("foo", "r").AndReturn(f)
        f.read(self.cmd.PART_SIZE).AndReturn("data")
        self.cmd.store.new_object(kind=obnamlib.FILEPART).AndReturn(part)
        self.cmd.store.put_object(part)
        fc.add(part.id)
        f.read(self.cmd.PART_SIZE).AndReturn(None)
        f.close()
        self.cmd.store.put_object(fc)

        self.mox.ReplayAll()
        self.cmd.backup_new_file("foo")
        self.mox.VerifyAll()
