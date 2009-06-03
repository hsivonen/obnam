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
import stat
import StringIO
import unittest

import obnamlib


class CatCommandTests(unittest.TestCase):

    def setUp(self):
        self.mox = mox.Mox()
        
        self.store = self.mox.CreateMock(obnamlib.Store)
        self.store.cat = \
            lambda host, output, contref, deltaref: output.write("foo")
        
        self.lookupper = self.mox.CreateMock(obnamlib.Lookupper)
        self.LookupperClass = lambda store, host, gen: self.lookupper

        self.host = self.mox.CreateMock(obnamlib.Host)
        self.host.id = "host.id"

        self.gen = self.mox.CreateMock(obnamlib.Generation)
        self.gen.id = "gen.id"

        self.fg = self.mox.CreateMock(obnamlib.FileGroup)
        self.fg.id = "fg.id"
        self.fg.names = ["file", "dir", "device"]

        self.gen.fgrefs = [self.fg.id]
        self.gen.dirrefs = []
        
        self.device = (obnamlib.make_stat(st_mode=stat.S_IFCHR), 
                       None, None, None, None)

        self.file = (obnamlib.make_stat(st_mode=stat.S_IFREG), 
                                        "file.cont", None, None, None)
        
        self.cmd = obnamlib.CatCommand()

    def cat(self, pathname, output=None):
        return self.cmd.cat(self.store, self.host.id, self.gen.id, pathname,
                        output=output, Lookupper=self.LookupperClass)

    def test_raises_exception_for_nonexistent_host(self):
        self.store.get_host(self.host.id).AndRaise(obnamlib.NotFound("foo"))
        self.mox.ReplayAll()
        self.assertRaises(obnamlib.NotFound, self.cat, "notexist")
        self.mox.VerifyAll()

    def test_raises_exception_for_nonexistent_generation(self):
        self.store.get_host(self.host.id).AndReturn(self.host)
        self.host.get_generation_id(self.gen.id).AndReturn(self.gen.id)
        self.store.get_object(self.host, self.gen.id).AndRaise(
            obnamlib.NotFound("foo"))
        self.mox.ReplayAll()
        self.assertRaises(obnamlib.NotFound, self.cat, "notexist")
        self.mox.VerifyAll()

    def test_raises_notfound_for_nonexistent_file(self):
        self.store.get_host(self.host.id).AndReturn(self.host)
        self.host.get_generation_id(self.gen.id).AndReturn(self.gen.id)
        self.store.get_object(self.host, self.gen.id).AndReturn(self.gen)
        self.lookupper.is_file("notexist").AndRaise(obnamlib.NotFound("foo"))
        self.mox.ReplayAll()
        self.assertRaises(obnamlib.NotFound, self.cat, "notexist")
        self.mox.VerifyAll()
        
    def test_raises_exception_for_directory(self):
        self.store.get_host(self.host.id).AndReturn(self.host)
        self.host.get_generation_id(self.gen.id).AndReturn(self.gen.id)
        self.store.get_object(self.host, self.gen.id).AndReturn(self.gen)
        self.lookupper.is_file("dir").AndReturn(False)
        self.mox.ReplayAll()
        self.assertRaises(obnamlib.Exception, self.cat, "dir")
        self.mox.VerifyAll()

    def test_raises_exception_for_irregular_file(self):
        self.store.get_host(self.host.id).AndReturn(self.host)
        self.host.get_generation_id(self.gen.id).AndReturn(self.gen.id)
        self.store.get_object(self.host, self.gen.id).AndReturn(self.gen.id)
        self.lookupper.is_file("device").AndReturn(True)
        self.lookupper.get_file("device").AndReturn(self.device)
        self.mox.ReplayAll()
        self.assertRaises(obnamlib.Exception, self.cat, "device")
        self.mox.VerifyAll()

    def test_returns_correct_contents_for_regular_file(self):
        self.store.get_host(self.host.id).AndReturn(self.host)
        self.host.get_generation_id(self.gen.id).AndReturn(self.gen.id)
        self.store.get_object(self.host, self.gen.id).AndReturn(self.gen)
        self.lookupper.is_file("file").AndReturn(True)
        self.lookupper.get_file("file").AndReturn(self.file)
        self.mox.ReplayAll()
        f = StringIO.StringIO()
        self.cat("file", output=f)
        self.mox.VerifyAll()
        self.assertEqual(f.getvalue(), "foo")
