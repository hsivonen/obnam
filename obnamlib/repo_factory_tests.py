# Copyright 2013  Lars Wirzenius
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
#
# =*= License: GPL-3+ =*=


import os
import shutil
import tempfile
import unittest

import obnamlib


class RepositoryFormatTests(unittest.TestCase):

    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        self.repodir = os.path.join(self.tempdir, 'repo')
        os.mkdir(self.repodir)

    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def test_raises_exception_for_unknown_format(self):
        fs = obnamlib.LocalFS(self.repodir)
        fs.write_file('metadata/format', 'unknown')
        factory = obnamlib.RepositoryFactory()
        self.assertRaises(
            obnamlib.UnknownRepositoryFormat,
            factory.open_existing_repo,
            fs)

    def test_accepts_good_format(self):
        good = obnamlib.RepositoryFormat6
        fs = obnamlib.LocalFS(self.repodir)
        fs.write_file('metadata/format', good.format)
        factory = obnamlib.RepositoryFactory()
        repo = factory.open_existing_repo(fs)
        self.assertTrue(isinstance(repo, good))

    def test_creates_a_new_repository(self):
        good = obnamlib.RepositoryFormat6
        fs = obnamlib.LocalFS(self.repodir)
        factory = obnamlib.RepositoryFactory()
        repo = factory.create_repo(fs, good)
        self.assertTrue(isinstance(repo, good))

    def test_raises_error_when_unknown_format_requested(self):
        fs = obnamlib.LocalFS(self.repodir)
        factory = obnamlib.RepositoryFactory()
        self.assertRaises(
            obnamlib.UnknownRepositoryFormatWanted, 
            factory.create_repo, fs, int)

    def test_create_repo_is_ok_with_existing_repo(self):
        good = obnamlib.RepositoryFormat6
        fs = obnamlib.LocalFS(self.repodir)
        fs.write_file('metadata/format', good.format)
        factory = obnamlib.RepositoryFactory()
        repo = factory.create_repo(fs, good)
        self.assertTrue(isinstance(repo, good))
