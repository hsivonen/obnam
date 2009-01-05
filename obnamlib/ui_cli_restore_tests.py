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


import os
import shutil
import tempfile
import unittest

import obnamlib


class RestoreCommandTests(unittest.TestCase):

    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
    
        self.root = os.path.join(self.tempdir, "root")
        os.mkdir(self.root)
        file(os.path.join(self.root, "foo"), "w").write("bar")
        
        self.store = os.path.join(self.tempdir, "store")
        os.mkdir(self.store)
        
        backup = obnamlib.BackupCommand()
        backup(None, ["host", self.store, self.root])
        
        store = obnamlib.Store(self.store, "r")
        host = store.get_host("host")
        self.gen_id = host.genrefs[0]

        self.target = os.path.join(self.tempdir, "target")
        os.mkdir(self.target)

        self.cmd = obnamlib.RestoreCommand()

    def tearDown(self):
        shutil.rmtree(self.tempdir)
        
    def test_restores_single_file_correctly(self):
        self.cmd(None, ["host", self.store, self.gen_id, self.target, "foo"])
        target_pathname = os.path.join(self.target, "foo")
        self.assert_(file(target_pathname).read(), "bar")
