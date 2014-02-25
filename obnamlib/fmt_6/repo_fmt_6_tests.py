# Copyright (C) 2013  Lars Wirzenius
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


import shutil
import tempfile

import obnamlib


class RepositoryFormat6Tests(obnamlib.RepositoryInterfaceTests):

    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        fs = obnamlib.LocalFS(self.tempdir)
        self.hooks = obnamlib.HookManager()
        obnamlib.RepositoryFormat6.setup_hooks(self.hooks)
        self.repo = obnamlib.RepositoryFormat6(hooks=self.hooks)
        self.repo.set_fs(fs)

    def tearDown(self):
        shutil.rmtree(self.tempdir)

