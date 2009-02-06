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

    def mock_helper(self, filename, st, contref, deltaref):
        self.filename = filename
        self.st = st
        self.contref = contref
        self.deltaref = deltaref

    def test_restore_file_calls_helper_correctly(self):
        name = obnamlib.FileName("filename")
        contref = obnamlib.Component(kind=obnamlib.CONTREF, string="contref")
        deltaref = obnamlib.Component(kind=obnamlib.DELTAREF, 
                                      string="deltaref")
        st = obnamlib.make_stat()
    
        file = obnamlib.File([name, obnamlib.encode_stat(st), 
                              contref, deltaref])

        self.mox.ReplayAll()
        self.cmd.restore_helper = self.mock_helper
        self.cmd.restore_file("dirname", file)
        self.mox.VerifyAll()
        self.assertEqual(self.filename, "dirname/filename")
        self.assertEqual(self.st, st)
        self.assertEqual(self.contref, "contref")
        self.assertEqual(self.deltaref, "deltaref")

    def mock_restore_file(self, dirname, file):
        self.dirname = dirname
        self.file = file

    def test_restore_generation_calls_restore_file_correctly(self):
        walker = self.mox.CreateMock(obnamlib.StoreWalker)
        cmd = obnamlib.RestoreCommand()
        cmd.vfs = self.mox.CreateMock(obnamlib.VirtualFileSystem)
        cmd.restore_file = self.mock_restore_file
        
        walker.walk_generation().AndReturn([("dirname", [], ["file"])])
        cmd.vfs.mkdir("dirname")

        self.mox.ReplayAll()
        cmd.restore_generation(walker)
        self.mox.VerifyAll()
        
        self.assertEqual(self.dirname, "dirname")
        self.assertEqual(self.file, "file")

    def test_restore_filename_calls_helper_correctly(self):
        lookupper = self.mox.CreateMock(obnamlib.Lookupper)
        vfs = self.mox.CreateMock(obnamlib.VirtualFileSystem)
        
        cmd = obnamlib.RestoreCommand()
        cmd.vfs = vfs
        cmd.restore_helper = self.mock_helper
        
        lookupper.get_file("foo/bar").AndReturn(("st", "contref", 
                                                 "sigref", "deltaref"))
        cmd.vfs.makedirs("foo")
        
        self.mox.ReplayAll()
        cmd.restore_filename(lookupper, "foo/bar")
        self.mox.VerifyAll()
        self.assertEqual(self.filename, "foo/bar")
        self.assertEqual(self.st, "st")
        self.assertEqual(self.contref, "contref")
        self.assertEqual(self.deltaref, "deltaref")

    def test_restore_dir_calls_restore_file_correctly(self):
        walker = self.mox.CreateMock(obnamlib.StoreWalker)
        cmd = obnamlib.RestoreCommand()
        cmd.vfs = self.mox.CreateMock(obnamlib.VirtualFileSystem)
        cmd.restore_file = self.mock_restore_file
        
        walker.walk("dirname").AndReturn([("dirname", [], ["file"])])
        cmd.vfs.mkdir("dirname")

        self.mox.ReplayAll()
        cmd.restore_dir(walker, "dirname")
        self.mox.VerifyAll()
        
        self.assertEqual(self.dirname, "dirname")
        self.assertEqual(self.file, "file")
