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


class StoreTests(unittest.TestCase):

    def setUp(self):
        self.dirname = tempfile.mkdtemp()

        self.ro_dirname = os.path.join(self.dirname, "ro")
        os.mkdir(self.ro_dirname)
        self.ro = obnamlib.Store(self.ro_dirname, "r")

        self.rw_dirname = os.path.join(self.dirname, "rw")
        os.mkdir(self.rw_dirname)
        self.rw = obnamlib.Store(self.rw_dirname, "w")

    def tearDown(self):
        shutil.rmtree(self.dirname)

    def test_accepts_readonly_mode(self):
        self.assertEqual(self.ro.check_mode("r"), None)

    def test_accepts_readwrite_mode(self):
        self.assertEqual(self.ro.check_mode("w"), None)

    def test_does_not_accept_other_mode(self):
        self.assertRaises(obnamlib.Exception, self.ro.check_mode, "a")

    def test_creates_a_new_object_of_desired_kind(self):
        obj = self.rw.new_object(kind=obnamlib.HOST)
        self.assertEqual(obj.kind, obnamlib.HOST)

    def test_refuses_to_create_new_object_in_readonly_mode(self):
        self.assertRaises(obnamlib.Exception, self.ro.new_object,
                          kind=obnamlib.HOST)

    def test_raises_exception_when_getting_nonexistent_object(self):
        self.assertRaises(obnamlib.Exception, self.ro.get_object, "foo")

    def test_raises_exception_when_getting_new_object_until_it_is_put(self):
        obj = self.rw.new_object(kind=obnamlib.GEN)
        self.assertRaises(obnamlib.Exception, self.rw.get_object, obj.id)

    def test_puts_and_then_gets_object(self):
        obj = self.rw.new_object(kind=obnamlib.GEN)
        self.rw.put_object(obj)
        self.assertEqual(self.rw.get_object(obj.id).id, obj.id)

    def test_refuses_to_put_object_twice(self):
        obj = self.rw.new_object(kind=obnamlib.GEN)
        self.rw.put_object(obj)
        self.assertRaises(obnamlib.Exception, self.rw.put_object, obj)

    def test_refuses_to_put_object_in_readonly_mode(self):
        self.assertRaises(obnamlib.Exception, self.ro.put_object, None)

    def test_commit_commits_to_disk(self):
        obj = self.rw.new_object(kind=obnamlib.GEN)
        self.rw.put_object(obj)
        self.rw.commit()

        store = obnamlib.Store(self.rw_dirname, "r")
        self.assertEqual(store.get_object(obj.id).id, obj.id)

    def test_refuses_to_commit_in_readonly_mode(self):
        self.assertRaises(obnamlib.Exception, self.ro.commit)
