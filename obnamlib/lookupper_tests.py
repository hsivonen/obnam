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
import tempfile
import unittest

import obnamlib


class SplitTests(unittest.TestCase):

    def setUp(self):
        self.lup = obnamlib.Lookupper(None, None, None)

    def test_returns_root_for_root(self):
        self.assertEqual(self.lup.split("/"), ["/"])
        
    def test_returns_self_for_basename(self):
        self.assertEqual(self.lup.split("foo"), ["foo"])
        
    def test_returns_parts_for_simple_path(self):
        self.assertEqual(self.lup.split("foo/bar"), ["foo", "bar"])
        
    def test_returns_parts_including_root_for_absolute_path(self):
        self.assertEqual(self.lup.split("/foo/bar"), ["/", "foo", "bar"])
        
    def test_returns_parts_including_root_for_short_absolute_path(self):
        self.assertEqual(self.lup.split("/foo"), ["/", "foo"])
        
    def test_returns_nonempty_last_part_when_path_ends_in_sep(self):
        self.assertEqual(self.lup.split("foo/bar/"), ["foo", "bar"])
        
    def test_returns_nonempty_last_part_when_short_path_ends_in_sep(self):
        self.assertEqual(self.lup.split("foo/"), ["foo"])
        
    def test_returns_parts_when_duplicate_separators(self):
        self.assertEqual(self.lup.split("foo//bar"), ["foo", "bar"])
        
    def test_returns_parts_when_duplicate_trailing_separators(self):
        self.assertEqual(self.lup.split("foo//bar//"), ["foo", "bar"])
        
    def test_returns_leading_root_when_duplicate_separator_after_root(self):
        self.assertEqual(self.lup.split("//foo//bar"), ["/", "foo", "bar"])


class DummyDir(object):

    def __init__(self, id, name, dirrefs, fgrefs):
        self.id = id
        self.name = name
        self.stat = obnamlib.make_stat(st_size=42)
        self.dirrefs = dirrefs
        self.fgrefs = fgrefs


class DummyGeneration(DummyDir):


    def __init__(self, id, dirrefs, fgrefs):
        self.id = id
        self.dirrefs = dirrefs
        self.fgrefs = fgrefs
    

class DummyFile(object):

    def __init__(self, name):
        self.name = name
        self.stat = obnamlib.make_stat(st_size=123)
        self.contref = name + ".cont"
        self.sigref = name + ".sig"
        self.deltaref = name + ".delta"

    
class DummyFileGroup(object):

    def __init__(self, id, files):
        self.id = id
        self.files = files

    @property
    def names(self):
        return [file.name for file in self.files]
        
    def get_file(self, name):
        for file in self.files:
            if file.name == name:
                return file.stat, file.contref, file.sigref, file.deltaref
        raise obnamlib.NotFound("foo")


class DummyStore(object):

    def __init__(self, objects):
        self.objects = dict((obj.id, obj) for obj in objects)

    def get_object(self, host, id):
        return self.objects[id]


class LookupperTests(unittest.TestCase):

    def setUp(self):
        self.subsubdir = DummyDir("subsubdir.id", "subsubdir", [], [])
        self.bar = DummyFile("bar")
        self.subfg = DummyFileGroup("subfg.id", [self.bar])
        self.subdir = DummyDir("subdir.id", "subdir", [self.subsubdir.id], 
                               [self.subfg.id])
        self.dir = DummyDir("dir.id", "dir", [self.subdir.id], [])
        self.foo = DummyFile("foo")
        self.fg = DummyFileGroup("fg.id", [self.foo])
        self.gen = DummyGeneration("gen.id", [self.dir.id], [self.fg.id])
        self.host = object()
        self.store = DummyStore([self.gen, self.fg, self.dir,
                                 self.subdir, self.subfg,
                                 self.subsubdir])

        self.lookupper = obnamlib.Lookupper(self.store, self.host, self.gen)

    def test_raises_notfound_if_file_not_found_in_root(self):
        self.assertRaises(obnamlib.NotFound, self.lookupper.get_file, "not")

    def test_raises_notfound_if_dir_not_found_in_root(self):
        self.assertRaises(obnamlib.NotFound, self.lookupper.get_dir, "not")

    def test_raises_notfound_if_file_not_found_deep_in_hierarchy(self):
        self.assertRaises(obnamlib.NotFound, self.lookupper.get_file,
                          "/dir/subdir/not")
 
    def test_raises_notfound_if_dir_not_found_deep_in_hierarchy(self):
        self.assertRaises(obnamlib.NotFound, self.lookupper.get_dir,
                          "/dir/subdir/not")
 
    def test_raises_notfound_if_dir_not_found_in_middle_of_path(self):
        self.assertRaises(obnamlib.NotFound, self.lookupper.get_dir,
                          "/dir/subdir/not/foo")
 
    def test_raises_notfound_if_file_not_found_in_filegroups(self):
        self.assertRaises(obnamlib.NotFound, 
                          self.lookupper.get_file_in_filegroups,
                          "not", self.gen.fgrefs)
 
    def test_finds_file_in_root(self):
        self.assertEqual(self.lookupper.get_file("foo"),
                         (self.foo.stat, "foo.cont", "foo.sig", "foo.delta"))

    def test_finds_dir_in_root(self):
        self.assertEqual(self.lookupper.get_dir("dir"), self.dir)

    def test_finds_file_deep_in_directory_hierarchy(self):
        self.assertEqual(self.lookupper.get_file("dir/subdir/bar"),
                         (self.bar.stat, "bar.cont", "bar.sig", "bar.delta"))

    def test_finds_dir_deep_in_directory_hierarchy(self):
        self.assertEqual(self.lookupper.get_dir("dir/subdir/subsubdir"),
                         self.subsubdir)

    def test_determines_type_correctly_for_file(self):
        self.assertEqual(self.lookupper.is_file("foo"), True)

    def test_determines_type_correctly_for_dir(self):
        self.assertEqual(self.lookupper.is_file("dir"), False)

    def test_raises_notfound_when_asked_for_type_of_nonexistent_file(self):
        self.assertRaises(obnamlib.NotFound, self.lookupper.is_file, "not")
