# Copyright (C) 2008  Lars Wirzenius <liw@iki.fi>
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


"""Unit tests for abstraction for storing backup data, for obnamlib."""


import os
import shutil
import socket
import tempfile
import unittest

import obnamlib


class StoreTests(unittest.TestCase):

    def setUp(self):
        context = obnamlib.context.Context()
        context.cache = obnamlib.Cache(context.config)
        context.be = obnamlib.backend.init(context.config, context.cache)
        self.store = obnamlib.Store(context)

    def tearDown(self):
        shutil.rmtree(self.store._context.config.get("backup", "store"),
                      ignore_errors=True)
        shutil.rmtree(self.store._context.config.get("backup", "cache"),
                      ignore_errors=True)

    def testReturnsNoneWhenNoHostBlockExists(self):
        self.failUnlessEqual(self.store.get_host_block(), None)

    def testReturnsAnActualHostBlockAfterFetch(self):
        self.store.fetch_host_block()
        host = self.store.get_host_block()
        self.failUnless(isinstance(host, obnamlib.obj.HostBlockObject))

    def testReturnsActualHostBlockWhenOneExists(self):
        self.store.fetch_host_block()
        self.store.commit_host_block([])
        
        context = obnamlib.context.Context()
        context.be = obnamlib.backend.init(context.config, context.cache)
        store = obnamlib.Store(context)
        store.fetch_host_block()
        host = store.get_host_block()
        self.failUnless(isinstance(host, obnamlib.obj.HostBlockObject))

    def testReplacesHostObjectInMemory(self):
        self.store.fetch_host_block()
        host = self.store.get_host_block()
        self.store.commit_host_block([])
        self.failIfEqual(self.store.get_host_block(), host)

    def testCreatesNewHostBlockWhenNoneExists(self):
        self.store.fetch_host_block()
        host = self.store.get_host_block()
        self.failUnlessEqual(host.get_id(), socket.gethostname())
        self.failUnlessEqual(host.get_generation_ids(), [])
        self.failUnlessEqual(host.get_map_block_ids(), [])
        self.failUnlessEqual(host.get_contmap_block_ids(), [])

    def testLoadsActualHostBlockWhenOneExists(self):
        context = obnamlib.context.Context()
        cache = obnamlib.Cache(context.config)
        context.be = obnamlib.backend.init(context.config, context.cache)
        host_id = context.config.get("backup", "host-id")
        temp = obnamlib.obj.HostBlockObject(host_id=host_id,
                                         gen_ids=["pink", "pretty"])
        obnamlib.io.upload_host_block(context, temp.encode())
        
        self.store.fetch_host_block()
        host = self.store.get_host_block()
        self.failUnlessEqual(host.get_generation_ids(), ["pink", "pretty"])

    def testGettingNonExistentObjectRaisesException(self):
        self.failUnlessRaises(obnamlib.exception.ObnamException,
                              self.store.get_object, "pink")

    def testAddsObjectToStore(self):
        o = obnamlib.obj.GenerationObject(id="pink")
        self.store.fetch_host_block()
        self.store.queue_object(o)
        self.store.commit_host_block([])
        
        context2 = obnamlib.context.Context()
        context2.cache = obnamlib.Cache(context2.config)
        context2.be = obnamlib.backend.init(context2.config, context2.cache)
        store2 = obnamlib.Store(context2)
        store2.fetch_host_block()
        store2.load_maps()
        self.failUnless(store2.get_object(o.get_id()))

    def mock_queue_object(self, object):
        self.queued_objects.append(object)
        
    def testAddsSeveralObjectsToStore(self):
        objs = [None, True, False]
        self.queued_objects = []
        self.store.queue_object = self.mock_queue_object
        self.store.queue_objects(objs)
        self.failUnlessEqual(objs, self.queued_objects)


class StoreMapTests(unittest.TestCase):

    def setUp(self):
        # First, set up two mappings.

        context = obnamlib.context.Context()
        context.cache = obnamlib.Cache(context.config)
        context.be = obnamlib.backend.init(context.config, context.cache)

        obnamlib.map.add(context.map, "pink", "pretty")
        obnamlib.map.add(context.contmap, "black", "beautiful")

        map_id = context.be.generate_block_id()
        map_block = obnamlib.map.encode_new_to_block(context.map, map_id)
        context.be.upload_block(map_id, map_block, True)

        contmap_id = context.be.generate_block_id()
        contmap_block = obnamlib.map.encode_new_to_block(context.contmap, 
                                                      contmap_id)
        context.be.upload_block(contmap_id, contmap_block, True)

        host_id = context.config.get("backup", "host-id")
        host = obnamlib.obj.HostBlockObject(host_id=host_id,
                                         map_block_ids=[map_id],
                                         contmap_block_ids=[contmap_id])
        obnamlib.io.upload_host_block(context, host.encode())

        # Then set up the real context and app.

        self.context = obnamlib.context.Context()
        self.context.cache = obnamlib.Cache(self.context.config)
        self.context.be = obnamlib.backend.init(self.context.config, 
                                             self.context.cache)
        self.store = obnamlib.Store(self.context)
        self.store.fetch_host_block()

    def tearDown(self):
        shutil.rmtree(self.store._context.config.get("backup", "store"),
                      ignore_errors=True)
        shutil.rmtree(self.store._context.config.get("backup", "cache"),
                      ignore_errors=True)

    def testHasNoMapsLoadedByDefault(self):
        self.failUnlessEqual(obnamlib.map.count(self.context.map), 0)

    def testHasNoContentMapsLoadedByDefault(self):
        self.failUnlessEqual(obnamlib.map.count(self.context.contmap), 0)

    def testLoadsMapsWhenRequested(self):
        self.store.load_maps()
        self.failUnlessEqual(obnamlib.map.count(self.context.map), 1)

    def testLoadsContentMapsWhenRequested(self):
        self.store.load_content_maps()
        self.failUnlessEqual(obnamlib.map.count(self.context.contmap), 1)

    def testAddsNoNewMapsWhenNothingHasChanged(self):
        self.store.update_maps()
        self.failUnlessEqual(obnamlib.map.count(self.context.map), 0)

    def testAddsANewMapsWhenSomethingHasChanged(self):
        obnamlib.map.add(self.context.map, "pink", "pretty")
        self.store.update_maps()
        self.failUnlessEqual(obnamlib.map.count(self.context.map), 1)

    def testAddsNoNewContentMapsWhenNothingHasChanged(self):
        self.store.update_content_maps()
        self.failUnlessEqual(obnamlib.map.count(self.context.contmap), 0)

    def testAddsANewContentMapsWhenSomethingHasChanged(self):
        obnamlib.map.add(self.context.contmap, "pink", "pretty")
        self.store.update_content_maps()
        self.failUnlessEqual(obnamlib.map.count(self.context.contmap), 1)


class StorePathnameParserTests(unittest.TestCase):

    def setUp(self):
        context = obnamlib.context.Context()
        self.store = obnamlib.Store(context)

    def testReturnsRootForRoot(self):
        self.failUnlessEqual(self.store.parse_pathname("/"), ["/"])

    def testReturnsDotForDot(self):
        self.failUnlessEqual(self.store.parse_pathname("."), ["."])

    def testReturnsItselfForSingleElement(self):
        self.failUnlessEqual(self.store.parse_pathname("foo"), ["foo"])

    def testReturnsListOfPartsForMultipleElements(self):
        self.failUnlessEqual(self.store.parse_pathname("foo/bar"), 
                             ["foo", "bar"])

    def testReturnsListOfPartsFromRootForAbsolutePathname(self):
        self.failUnlessEqual(self.store.parse_pathname("/foo/bar"), 
                             ["/", "foo", "bar"])

    def testIgnoredTrailingSlashIfNotRoot(self):
        self.failUnlessEqual(self.store.parse_pathname("foo/bar/"), 
                             ["foo", "bar"])


class StoreLookupTests(unittest.TestCase):

    def create_data_dir(self):
        dirname = tempfile.mkdtemp()
        file(os.path.join(dirname, "file1"), "w").close()
        os.mkdir(os.path.join(dirname, "dir1"))
        os.mkdir(os.path.join(dirname, "dir1", "dir2"))
        file(os.path.join(dirname, "dir1", "dir2", "file2"), "w").close()
        return dirname

    def create_context(self):
        context = obnamlib.context.Context()
        context.cache = obnamlib.Cache(context.config)
        context.be = obnamlib.backend.init(context.config, context.cache)
        return context

    def setUp(self):
        self.datadir = self.create_data_dir()

        app = obnamlib.Application(self.create_context())
        app.load_host()
        gen = app.backup([self.datadir])
        app.get_store().commit_host_block([gen])
        
        self.store = obnamlib.Store(self.create_context())
        self.store.fetch_host_block()
        self.store.load_maps()
        gen_ids = self.store.get_host_block().get_generation_ids()
        self.gen = self.store.get_object(gen_ids[0])

    def tearDown(self):
        shutil.rmtree(self.datadir)
        shutil.rmtree(self.store._context.config.get("backup", "store"))

    def testFindsBackupRoot(self):
        dir = self.store.lookup_dir(self.gen, self.datadir)
        self.failUnless(dir.get_name(), self.datadir)

    def testFindsFirstSubdir(self):
        pathname = os.path.join(self.datadir, "dir1")
        dir = self.store.lookup_dir(self.gen, pathname)
        self.failUnless(dir.get_name(), "dir1")

    def testFindsSecondSubdir(self):
        pathname = os.path.join(self.datadir, "dir1", "dir2")
        dir = self.store.lookup_dir(self.gen, pathname)
        self.failUnless(dir.get_name(), "dir2")

    def testDoesNotFindNonExistentDir(self):
        self.failUnlessEqual(self.store.lookup_dir(self.gen, "notexist"),
                             None)

    def testDoesNotFindNonExistentFileInSubDirectory(self):
        pathname = os.path.join(self.datadir, "dir1", "notexist")
        file = self.store.lookup_file(self.gen, pathname)
        self.failUnlessEqual(file, None)

    def testDoesNotFindNonExistentFileInSubSubDirectory(self):
        pathname = os.path.join(self.datadir, "dir1", "dir2", "notexist")
        file = self.store.lookup_file(self.gen, pathname)
        self.failUnlessEqual(file, None)

    def testDoesNotFindNonExistentFileInRoot(self):
        pathname = os.path.join(self.datadir, "notexist")
        file = self.store.lookup_file(self.gen, pathname)
        self.failUnlessEqual(file, None)

    def filename(self, file):
        return file.first_string_by_kind(obnamlib.cmp.FILENAME)

    def testFindsFileInRootDirectory(self):
        pathname = os.path.join(self.datadir, "file1")
        file = self.store.lookup_file(self.gen, pathname)
        self.failUnlessEqual(self.filename(file), "file1")

    def testFindsFileInSubDirectory(self):
        pathname = os.path.join(self.datadir, "dir1", "dir2", "file2")
        file = self.store.lookup_file(self.gen, pathname)
        self.failUnlessEqual(self.filename(file), "file2")
