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
import os
import shutil
import StringIO
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

        self.mox = mox.Mox()

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
        host = self.rw.get_host("foobar")
        self.assertRaises(obnamlib.NotFound, self.rw.get_object, host, "foo")

    def test_get_object_raises_exception_if_object_not_found_in_block(self):
        host = self.rw.get_host("foobar")
        self.rw.commit(host)
        self.rw.objmap["yo"] = "foobar" # introduce fake mapping
        self.assertRaises(obnamlib.NotFound, self.rw.get_object, host, "yo")

    def test_raises_exception_when_getting_new_object_until_it_is_put(self):
        host = self.rw.get_host("foo")
        obj = self.rw.new_object(kind=obnamlib.GEN)
        self.assertRaises(obnamlib.NotFound, self.rw.get_object, host, obj.id)

    def test_refuses_to_put_object_in_readonly_mode(self):
        self.assertRaises(obnamlib.Exception, self.ro.put_object, None)

    def test_put_object_puts_object_into_object_queue(self):
        obj = self.rw.new_object(kind=obnamlib.GEN)
        self.rw.put_object(obj)
        self.assert_(obj in self.rw.object_queue)

    def test_has_no_new_mappings_initially(self):
        self.assertEqual(self.rw.new_mappings, {})

    def test_adds_mapping_correctly(self):
        self.rw.add_mapping("host", "obj", "block")
        self.assertEqual(self.rw.new_mappings,
                         { "host": { "obj": "block" }})

    def test_push_objects_outputs_block(self):
        self.rw.fs = self.mox.CreateMock(obnamlib.VirtualFileSystem)
        self.rw.idgen = self.mox.CreateMock(obnamlib.BlockIdGenerator)
        host = self.mox.CreateMock(obnamlib.Host)
        obj = self.rw.new_object(kind=obnamlib.GEN)

        id = self.rw.idgen.new_id().AndReturn("blockid")
        self.rw.fs.write_file("blockid", mox.IsA(str))
        self.rw.add_mapping(host, obj.id, "blockid")

        self.mox.ReplayAll()
        self.rw.put_object(obj)
        self.rw.push_objects(host)
        self.mox.VerifyAll()
        self.assertEqual(self.rw.object_queue, [])

    def test_push_new_mappings_does_nothing_if_there_are_no_new_objects(self):
        host = self.mox.CreateMock(obnamlib.Host)
        self.rw.new_mappings[host] = {}
        self.mox.ReplayAll()
        self.rw.push_new_mappings(host)
        self.mox.VerifyAll()
        self.assertEqual(self.rw.new_mappings[host], {})
    
    def test_push_new_mappings_writes_out_a_new_mapping_block(self):
        host = self.mox.CreateMock(obnamlib.Host)
        host.maprefs = self.mox.CreateMock(list)
        self.rw.idgen = self.mox.CreateMock(obnamlib.BlockIdGenerator)
        self.rw.fs = self.mox.CreateMock(obnamlib.VirtualFileSystem)
        self.rw.add_mapping(host, "foo", "bar")
        
        block_id = self.rw.idgen.new_id().AndReturn("blockid")
        self.rw.fs.write_file(block_id, mox.IsA(str))
        host.maprefs.append(block_id)

        self.mox.ReplayAll()
        self.rw.push_new_mappings(host)
        self.mox.VerifyAll()
        self.assertEqual(self.rw.new_mappings[host], {})

    def test_commit_commits_to_disk(self):
        host = self.rw.get_host("foo")
        obj = self.rw.new_object(kind=obnamlib.GEN)
        self.rw.put_object(obj)
        self.rw.commit(host)

        store = obnamlib.Store(self.rw_dirname, "r")
        self.assertEqual(store.get_object(host, obj.id).id, obj.id)

    def test_commit_pushes_objects(self):
        self.pushed = False
        def mock_push(host):
            self.pushed = True
        self.rw.push_objects = mock_push

        host = self.rw.get_host("foo")
        obj = self.rw.new_object(kind=obnamlib.GEN)
        self.rw.put_object(obj)
        self.rw.commit(host)
        self.assert_(self.pushed)

    def test_refuses_to_commit_in_readonly_mode(self):
        self.assertRaises(obnamlib.Exception, self.ro.commit, None)

    def test_get_host_on_readonly_when_none_exists_fails(self):
        self.assertRaises(obnamlib.Exception, self.ro.get_host, "foo")

    def test_get_host_creates_new_one_when_none_exists(self):
        host = self.rw.get_host("foo")
        self.assert_(isinstance(host, obnamlib.Host))
        self.assertEquals(host.id, "foo")
        self.assertEquals(host.components, [])

    def test_get_host_loads_existing_object_when_one_exists(self):
        host = self.rw.get_host("foo")
        host.genrefs.append("genref")
        self.rw.commit(host)
        
        store = obnamlib.Store(self.rw_dirname, "r")
        host2 = store.get_host("foo")
        self.assertEqual(host2.genrefs, ["genref"])

    def test_get_host_raises_notfound_if_host_block_does_not_contain_it(self):
        bf = obnamlib.BlockFactory()
        encoded = bf.encode_block("foo", [], {})
        self.rw.fs.write_file("foo", encoded)
        
        self.assertRaises(obnamlib.NotFound, self.rw.get_host, "foo")

    def test_find_block_does_not_find_anything_in_empty_store(self):
        host = self.rw.get_host("host")
        self.assertRaises(obnamlib.NotFound, self.rw.find_block, host, "foo")

    def test_find_block_does_not_find_object_that_has_just_been_put(self):
        host = self.rw.get_host("host")
        obj = self.rw.new_object(kind=obnamlib.GEN)
        self.rw.put_object(obj)
        self.assertRaises(obnamlib.NotFound, self.rw.find_block, host, obj.id)

    def test_find_block_finds_object_after_commit(self):
        host = self.rw.get_host("foo")
        obj = self.rw.new_object(kind=obnamlib.GEN)
        self.rw.put_object(obj)
        self.rw.commit(host)
        
        rw2 = obnamlib.Store(self.rw_dirname, "w")
        self.assertNotEqual(rw2.find_block(host, obj.id), None)

    def test_find_block_finds_from_cache_the_second_time(self):
        host = self.rw.get_host("foo")
        obj = self.rw.new_object(kind=obnamlib.GEN)
        self.rw.put_object(obj)
        self.rw.commit(host)
        
        rw2 = obnamlib.Store(self.rw_dirname, "w")
        rw2.find_block(host, obj.id)
        rw2.fs = None # This breaks find_block unless there's a cache hit
        self.assertNotEqual(rw2.find_block(host, obj.id), None)

    def test_cat_gets_nonexistent_contents_correctly(self):
        f = StringIO.StringIO()
        self.rw.cat(None, f, None, None)
        self.assertEqual(f.getvalue(), "")

    def test_cat_gets_simple_file_contents_correctly(self):
        filepart = obnamlib.FilePart(id="part.id", data="foo")
        filecont = obnamlib.FileContents(id="cont.id")
        filecont.add(filepart.id)

        host = self.rw.get_host("host.id")
        self.rw.put_object(filepart)
        self.rw.put_object(filecont)
        self.rw.commit(host)
        
        f = StringIO.StringIO()
        store = obnamlib.Store(self.rw_dirname, "r")
        host = store.get_host("host.id")
        store.cat(host, f, filecont.id, None)
        self.assertEqual(f.getvalue(), "foo")

    def test_put_contents_puts_contents_correctly(self):
        f = StringIO.StringIO("foo")
        host = self.rw.get_host("host.id")
        filecont = self.rw.put_contents(f, 1024)
        self.rw.commit(host)

        result = StringIO.StringIO()
        store = obnamlib.Store(self.rw_dirname, "r")
        host = store.get_host("host.id")
        store.cat(host, result, filecont.id, None)
        self.assertEqual(result.getvalue(), "foo")
