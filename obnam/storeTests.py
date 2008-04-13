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


"""Unit tests for abstraction for storing backup data, for Obnam."""


import shutil
import unittest

import obnam


class StoreTests(unittest.TestCase):

    def setUp(self):
        context = obnam.context.Context()
        context.cache = obnam.cache.Cache(context.config)
        context.be = obnam.backend.init(context.config, context.cache)
        self.store = obnam.Store(context)

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
        self.failUnless(isinstance(host, obnam.obj.HostBlockObject))

    def testReturnsActualHostBlockWhenOneExists(self):
        self.store.fetch_host_block()
        self.store.commit_host_block()
        
        context = obnam.context.Context()
        context.be = obnam.backend.init(context.config, context.cache)
        store = obnam.Store(context)
        store.fetch_host_block()
        host = store.get_host_block()
        self.failUnless(isinstance(host, obnam.obj.HostBlockObject))

    def testGettingNonExistentObjectRaisesException(self):
        self.failUnlessRaises(obnam.exception.ObnamException,
                              self.store.get_object, "pink")

    def testAddsObjectToStore(self):
        o = obnam.obj.GenerationObject(id="pink")
        self.store.fetch_host_block()
        self.store.queue_object(o)
        self.store.commit_host_block()
        
        context = obnam.context.Context()
        context.cache = obnam.cache.Cache(context.config)
        context.be = obnam.backend.init(context.config, context.cache)
        store = obnam.Store(context)
        store.fetch_host_block()
        store.load_maps()
        self.failUnless(store.get_object(o.get_id()))
