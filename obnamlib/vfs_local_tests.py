# Copyright (C) 2008-2014  Lars Wirzenius <liw@liw.fi>
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

import platform
import errno
import os
import shutil
import tempfile
import unittest

import cliapp

import obnamlib
from obnamlib import _obnam


class LocalFSTests(obnamlib.VfsTests, unittest.TestCase):

    def setUp(self):
        self.basepath = tempfile.mkdtemp()
        self.fs = obnamlib.LocalFS(self.basepath)

    def tearDown(self):
        self.fs.close()
        shutil.rmtree(self.basepath)

    def test_joins_relative_path_ok(self):
        self.assertEqual(self.fs.join('foo'),
                         os.path.join(self.basepath, 'foo'))

    def test_join_treats_absolute_path_as_absolute(self):
        self.assertEqual(self.fs.join('/foo'), '/foo')

    def test_get_username_returns_root_for_zero(self):
        self.assertEqual(self.fs.get_username(0), 'root')

    def test_get_groupname_returns_root_for_zero(self):
        root = 'wheel' if platform.system() == 'FreeBSD' else 'root'
        self.assertEqual(self.fs.get_groupname(0), root)


class XAttrTests(unittest.TestCase):
    '''Tests for extended attributes.'''

    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        self.filename = os.path.join(self.tempdir, 'file.txt')
        self.other = os.path.join(self.tempdir, 'other.txt')

    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def user_xattr_are_supported(self):
        # Not all filesystems, or mounts of them, support extended
        # attributes. In order to not fail, we verify that things
        # work. We do this by checking if we can set a user.foo
        # attribute with the command line tool.

        try:
            exit, out, err = cliapp.runcmd_unchecked(
                ['setfattr', '-n', 'user.foo', 'bar', self.other])
        except OSError:
            # Either xattr aren't supported, or setfattr isn't
            # installed and we can't test.
            return False
        return exit == 0

    def test_empty_list(self):
        '''A new file has no extended attributes.'''

        if self.user_xattr_are_supported():
            self.assertEqual(_obnam.llistxattr(self.filename), "")

    def test_lsetxattr(self):
        '''lsetxattr() sets an attribute on a file.'''

        if self.user_xattr_are_supported():
            _obnam.lsetxattr(self.filename, "user.key", "value")
            _obnam.lsetxattr(self.filename, "user.hello", "world")
            ret = _obnam.llistxattr(self.filename)

            self.assertEqual(
                sorted(ret.strip("\0").split("\0")),
                ["user.hello", "user.key"])

    def test_lgetxattr(self):
        '''lgetxattr() gets the value of an attribute set on the file.'''

        if self.user_xattr_are_supported():
            _obnam.lsetxattr(self.filename, "user.hello", "world")
            self.assertEqual(
                _obnam.lgetxattr(self.filename, "user.hello"),
                "world")
