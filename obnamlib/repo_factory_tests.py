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


import unittest

import obnamlib


class DummyFS(object):

    def __init__(self):
        self.items = []

    def exists(self, filename):
        return filename in self.items

    def makedirs(self, filename):
        self.items.append(filename)


class RepositoryFactoryTests(unittest.TestCase):

    def setUp(self):
        self.fs = DummyFS()
        self.repo_factory = obnamlib.RepositoryFactory(self.fs)

    def test_fails_to_open_nonexistent_repo(self):
        self.assertRaises(
            obnamlib.RepositoryDoesNotExist,
            self.repo_factory.open_repository, 'foo')

    def test_creates_nonexistent_repo(self):
        pass

    def test_opens_existing_repo_when_creation_not_requested(self):
        pass

    def test_opens_existing_repo_when_creation_is_requested(self):
        pass

