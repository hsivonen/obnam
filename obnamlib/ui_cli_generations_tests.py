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


import mox
import StringIO
import unittest

import obnamlib


class GenerationsTests(unittest.TestCase):

    def setUp(self):
        self.mox = mox.Mox()
        self.output = StringIO.StringIO()
        self.cmd = obnamlib.GenerationsCommand()
        self.cmd.store = self.mox.CreateMock(obnamlib.Store)
        self.host = self.mox.CreateMock(obnamlib.Host)

    def test_shows_nothing_for_empty_host(self):
        self.host.genrefs = []
        self.cmd.store.get_host("foo").AndReturn(self.host)

        self.mox.ReplayAll()
        self.cmd.generations("foo")
        self.mox.VerifyAll()
        self.assertEqual(self.output.getvalue(), "")

    def test_shows_generations_in_the_right_order(self):
        self.host.genrefs = ["gen1", "gen2"]
        self.cmd.store.get_host("foo").AndReturn(self.host)

        self.mox.ReplayAll()
        self.cmd.generations("foo", output=self.output)
        self.mox.VerifyAll()
        self.assertEqual(self.output.getvalue(), "gen1\ngen2\n")
