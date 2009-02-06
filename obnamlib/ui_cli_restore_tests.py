# Copyright (C) 2009  Lars Wirzenius <liw@liw.fi>
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


import mox
import unittest

import obnamlib


class RestoreCommandTests(unittest.TestCase):

    def setUp(self):
        self.mox = mox.Mox()
        self.cmd = obnamlib.RestoreCommand()

    def test_helper_restores_file_contents(self):
        fs = self.mox.CreateMock(obnamlib.VirtualFileSystem)
        f = self.mox.CreateMock(file)
        store = self.mox.CreateMock(obnamlib.Store)
        
        self.cmd.vfs = fs
        self.cmd.store = store
        self.cmd.host = "host"

        fs.open("foo", "w").AndReturn(f)
        store.cat("host", f, "contref", "deltaref")
        f.close()
        
        self.mox.ReplayAll()
        self.cmd.restore_helper("foo", "st", "contref", "deltaref")
        self.mox.VerifyAll()
