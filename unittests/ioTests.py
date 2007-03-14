# Copyright (C) 2006  Lars Wirzenius <liw@iki.fi>
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


"""Unit tests for obnam.io"""


import os
import shutil
import tempfile
import unittest


import obnam


class ExceptionTests(unittest.TestCase):

    def testMissingBlock(self):
        e = obnam.io.MissingBlock("pink", "pretty")
        self.failUnless("pink" in str(e))
        self.failUnless("pretty" in str(e))

    def testFileContentsObjectMissing(self):
        e = obnam.io.FileContentsObjectMissing("pink")
        self.failUnless("pink" in str(e))


class ResolveTests(unittest.TestCase):

    def test(self):
        context = obnam.context.Context()
        # We don't need the fields that are usually initialized manually.

        facit = (
            (".", "/", "/"),
            (".", "/pink", "/pink"),
            (".", "pink", "./pink"),
            ("pink", "/", "/"),
            ("pink", "/pretty", "/pretty"),
            ("pink", "pretty", "pink/pretty"),
            ("/pink", "/", "/"),
            ("/pink", "/pretty", "/pretty"),
            ("/pink", "pretty", "/pink/pretty"),
            ("/", "/", "/"),
        )

        for target, pathname, resolved in facit:
            context.config.set("backup", "target-dir", target)
            x = obnam.io.resolve(context, pathname)
            self.failUnlessEqual(x, resolved)
            self.failUnlessEqual(obnam.io.unsolve(context, x), pathname)

        self.failUnlessEqual(obnam.io.unsolve(context, "/pink"), "pink")


class IoBase(unittest.TestCase):

    def setUp(self):
        self.cachedir = "tmp.cachedir"
        self.rootdir = "tmp.rootdir"
        
        os.mkdir(self.cachedir)
        os.mkdir(self.rootdir)
        
        config_list = (
            ("backup", "cache", self.cachedir),
            ("backup", "store", self.rootdir)
        )
    
        self.context = obnam.context.Context()
    
        for section, item, value in config_list:
            self.context.config.set(section, item, value)

        self.context.cache = obnam.cache.Cache(self.context.config)
        self.context.be = obnam.backend.init(self.context.config, 
                                                self.context.cache)

    def tearDown(self):
        shutil.rmtree(self.cachedir)
        shutil.rmtree(self.rootdir)
        del self.cachedir
        del self.rootdir
        del self.context


class ObjectQueueFlushing(IoBase):

    def testEmptyQueue(self):
        obnam.io.flush_object_queue(self.context, self.context.oq, 
                                       self.context.map)
        list = self.context.be.list()
        self.failUnlessEqual(list, [])

    def testFlushing(self):
        self.context.oq.add("pink", "pretty")
        
        self.failUnlessEqual(self.context.be.list(), [])
        
        obnam.io.flush_object_queue(self.context, self.context.oq,
                                       self.context.map)

        list = self.context.be.list()
        self.failUnlessEqual(len(list), 1)
        
        b1 = os.path.basename(obnam.map.get(self.context.map, "pink"))
        b2 = os.path.basename(list[0])
        self.failUnlessEqual(b1, b2)

    def testFlushAll(self):
        self.context.oq.add("pink", "pretty")
        self.context.content_oq.add("x", "y")
        obnam.io.flush_all_object_queues(self.context)
        self.failUnlessEqual(len(self.context.be.list()), 2)
        self.failUnless(self.context.oq.is_empty())
        self.failUnless(self.context.content_oq.is_empty())


class GetObjectTests(IoBase):

    def upload_object(self, object_id, object):
        self.context.oq.add(object_id, object)
        obnam.io.flush_object_queue(self.context, self.context.oq,
                                       self.context.map)

    def testGetObject(self):
        id = "pink"
        component = obnam.cmp.Component(42, "pretty")
        object = obnam.obj.Object(id, 0)
        object.add(component)
        object = object.encode()
        self.upload_object(id, object)
        o = obnam.io.get_object(self.context, id)

        self.failUnlessEqual(o.get_id(), id)
        self.failUnlessEqual(o.get_kind(), 0)
        list = o.get_components()
        self.failUnlessEqual(len(list), 1)
        self.failUnlessEqual(list[0].get_kind(), 42)
        self.failUnlessEqual(list[0].get_string_value(), "pretty")


class HostBlock(IoBase):

    def testFetchHostBlock(self):
        host_id = self.context.config.get("backup", "host-id")
        host = obnam.obj.HostBlockObject(host_id, ["gen1", "gen2"],
                                         ["map1", "map2"], 
                                         ["contmap1", "contmap2"])
        host = host.encode()
        be = obnam.backend.init(self.context.config, self.context.cache)
        
        obnam.io.upload_host_block(self.context, host)
        host2 = obnam.io.get_host_block(self.context)
        self.failUnlessEqual(host, host2)


class ObjectQueuingTests(unittest.TestCase):

    def find_block_files(self, config):
        files = []
        root = config.get("backup", "store")
        for dirpath, _, filenames in os.walk(root):
            files += [os.path.join(dirpath, x) for x in filenames]
        files.sort()
        return files

    def testEnqueue(self):
        context = obnam.context.Context()
        object_id = "pink"
        object = "pretty"
        context.config.set("backup", "block-size", "%d" % 128)
        context.cache = obnam.cache.Cache(context.config)
        context.be = obnam.backend.init(context.config, context.cache)

        self.failUnlessEqual(self.find_block_files(context.config), [])
        
        obnam.io.enqueue_object(context, context.oq, context.map, 
                                   object_id, object)
        
        self.failUnlessEqual(self.find_block_files(context.config), [])
        self.failUnlessEqual(context.oq.combined_size(), len(object))
        
        object_id2 = "pink2"
        object2 = "x" * 1024

        obnam.io.enqueue_object(context, context.oq, context.map, 
                                   object_id2, object2)
        
        self.failUnlessEqual(len(self.find_block_files(context.config)), 1)
        self.failUnlessEqual(context.oq.combined_size(), len(object2))

        shutil.rmtree(context.config.get("backup", "cache"), True)
        shutil.rmtree(context.config.get("backup", "store"), True)


class FileContentsTests(unittest.TestCase):

    def setUp(self):
        self.context = obnam.context.Context()
        self.context.cache = obnam.cache.Cache(self.context.config)
        self.context.be = obnam.backend.init(self.context.config, 
                                                self.context.cache)

    def tearDown(self):
        for x in ["cache", "store"]:
            if os.path.exists(self.context.config.get("backup", x)):
                shutil.rmtree(self.context.config.get("backup", x))

    def testEmptyFile(self):
        (fd, filename) = tempfile.mkstemp()
        os.close(fd)
        
        id = obnam.io.create_file_contents_object(self.context, filename)

        self.failIfEqual(id, None)
        self.failUnlessEqual(self.context.oq.ids(), [id])
        self.failUnlessEqual(obnam.map.count(self.context.map), 0)
            # there's no mapping yet, because the queue is small enough
            # that there has been no need to flush it

        os.remove(filename)

    def testNonEmptyFile(self):
        block_size = 16
        self.context.config.set("backup", "block-size", "%d" % block_size)
        filename = "Makefile"
        
        id = obnam.io.create_file_contents_object(self.context, filename)

        self.failIfEqual(id, None)
        self.failUnlessEqual(self.context.oq.ids(), [id])

    def testRestore(self):
        block_size = 16
        self.context.config.set("backup", "block-size", "%d" % block_size)
        filename = "Makefile"
        
        id = obnam.io.create_file_contents_object(self.context, filename)
        obnam.io.flush_object_queue(self.context, self.context.oq,
                                       self.context.map)
        obnam.io.flush_object_queue(self.context, self.context.content_oq,
                                       self.context.contmap)
        
        (fd, name) = tempfile.mkstemp()
        obnam.io.copy_file_contents(self.context, fd, id)
        os.close(fd)
        
        f = file(name, "r")
        data1 = f.read()
        f.close()
        os.remove(name)
        
        f = file(filename, "r")
        data2 = f.read()
        f.close()
        
        self.failUnlessEqual(data1, data2)


class MetaDataTests(unittest.TestCase):

    def testSet(self):
        (fd, name) = tempfile.mkstemp()
        os.close(fd)
        
        st1 = os.stat(name)
        inode = obnam.filelist.create_file_component_from_stat(name, st1, 
                                                               None, None,
                                                               None)

        os.chmod(name, 0)
        
        obnam.io.set_inode(name, inode)
        
        st2 = os.stat(name)
        
        self.failUnlessEqual(st1.st_mode, st2.st_mode)
        self.failUnlessEqual(st1.st_atime, st2.st_atime)
        self.failUnlessEqual(st1.st_mtime, st2.st_mtime)


class ObjectCacheTests(unittest.TestCase):

    def setUp(self):
        self.object = obnam.obj.Object("pink", 1)
        self.object2 = obnam.obj.Object("pretty", 1)
        self.object3 = obnam.obj.Object("beautiful", 1)

    def testCreate(self):
        context = obnam.context.Context()
        oc = obnam.io.ObjectCache(context)
        self.failUnlessEqual(oc.size(), 0)
        self.failUnless(oc.MAX > 0)
        
    def testPut(self):
        context = obnam.context.Context()
        oc = obnam.io.ObjectCache(context)
        self.failUnlessEqual(oc.get("pink"), None)
        oc.put(self.object)
        self.failUnlessEqual(oc.get("pink"), self.object)

    def testPutWithOverflow(self):
        context = obnam.context.Context()
        oc = obnam.io.ObjectCache(context)
        oc.MAX = 1
        oc.put(self.object)
        self.failUnlessEqual(oc.size(), 1)
        self.failUnlessEqual(oc.get("pink"), self.object)
        oc.put(self.object2)
        self.failUnlessEqual(oc.size(), 1)
        self.failUnlessEqual(oc.get("pink"), None)
        self.failUnlessEqual(oc.get("pretty"), self.object2)

    def testPutWithOverflowPart2(self):
        context = obnam.context.Context()
        oc = obnam.io.ObjectCache(context)
        oc.MAX = 2

        oc.put(self.object)
        oc.put(self.object2)
        self.failUnlessEqual(oc.size(), 2)
        self.failUnlessEqual(oc.get("pink"), self.object)
        self.failUnlessEqual(oc.get("pretty"), self.object2)

        oc.get("pink")
        oc.put(self.object3)
        self.failUnlessEqual(oc.size(), 2)
        self.failUnlessEqual(oc.get("pink"), self.object)
        self.failUnlessEqual(oc.get("pretty"), None)
        self.failUnlessEqual(oc.get("beautiful"), self.object3)


class ReachabilityTests(IoBase):

    def testNoDataNoMaps(self):
        host_id = self.context.config.get("backup", "host-id")
        host = obnam.obj.HostBlockObject(host_id, [], [], []).encode()
        obnam.io.upload_host_block(self.context, host)
        
        list = obnam.io.find_reachable_data_blocks(self.context, host)
        self.failUnlessEqual(list, [])
        
        list2 = obnam.io.find_map_blocks_in_use(self.context, host, list)
        self.failUnlessEqual(list2, [])

    def testNoDataExtraMaps(self):
        obnam.map.add(self.context.map, "pink", "pretty")
        map_block_id = "box"
        map_block = obnam.map.encode_new_to_block(self.context.map,
                                                         map_block_id)
        self.context.be.upload(map_block_id, map_block)

        obnam.map.add(self.context.contmap, "black", "beautiful")
        contmap_block_id = "fiddly"
        contmap_block = obnam.map.encode_new_to_block(
                            self.context.contmap, contmap_block_id)
        self.context.be.upload(contmap_block_id, contmap_block)

        host_id = self.context.config.get("backup", "host-id")
        host = obnam.obj.HostBlockObject(host_id, [], [map_block_id], 
                                         [contmap_block_id])
        host = host.encode()
        obnam.io.upload_host_block(self.context, host)
        
        list = obnam.io.find_map_blocks_in_use(self.context, host, [])
        self.failUnlessEqual(list, [])

    def testDataAndMap(self):
        o = obnam.obj.Object("rouge", obnam.obj.FILEPART)
        c = obnam.cmp.Component(obnam.cmp.FILECHUNK, "moulin")
        o.add(c)
        encoded_o = o.encode()
        
        block_id = "pink"
        oq = obnam.obj.ObjectQueue()
        oq.add("rouge", encoded_o)
        block = oq.as_block(block_id)
        self.context.be.upload(block_id, block)

        obnam.map.add(self.context.contmap, "rouge", block_id)
        map_block_id = "pretty"
        map_block = obnam.map.encode_new_to_block(self.context.contmap,
                                                         map_block_id)
        self.context.be.upload(map_block_id, map_block)

        host_id = self.context.config.get("backup", "host-id")
        host = obnam.obj.HostBlockObject(host_id, [], [], [map_block_id])
        host = host.encode()
        obnam.io.upload_host_block(self.context, host)
        
        list = obnam.io.find_map_blocks_in_use(self.context, host, 
                                                  [block_id])
        self.failUnlessEqual(list, [map_block_id])


class GarbageCollectionTests(IoBase):

    def testFindUnreachableFiles(self):
        host_id = self.context.config.get("backup", "host-id")
        host = obnam.obj.HostBlockObject(host_id, [], [], []).encode()
        obnam.io.upload_host_block(self.context, host)

        block_id = self.context.be.generate_block_id()
        self.context.be.upload(block_id, "pink")

        files = self.context.be.list()
        self.failUnlessEqual(files, [host_id, block_id])

        obnam.io.collect_garbage(self.context, host)
        files = self.context.be.list()
        self.failUnlessEqual(files, [host_id])


class ObjectCacheRegressionTest(unittest.TestCase):

    # This test case is for a bug in obnam.io.ObjectCache: with the
    # right sequence of operations, the cache can end up in a state where
    # the MRU list is too long, but contains two instances of the same
    # object ID. When the list is shortened, the first instance of the
    # ID is removed, and the object is also removed from the dictionary.
    # If the list is still too long, it is shortened again, by removing
    # the last item in the list, but that no longer is in the dictionary,
    # resulting in the shortening not happening. Voila, an endless loop.
    #
    # As an example, if the object queue maximum size is 3, the following
    # sequence exhibits the problem:
    #
    #       put('a')        mru = ['a']
    #       put('b')        mru = ['b', 'a']
    #       put('c')        mru = ['c', 'b', 'a']
    #       put('a')        mru = ['a', 'c', 'b', 'a'], shortened into
    #                           ['c', 'b', 'a'], and now dict no longer
    #                           has 'a'
    #       put('d')        mru = ['d', 'c', 'b', 'a'], which needs to be
    #                           shortened by removing the last element, but
    #                           since 'a' is no longer in dict, the list
    #                           doesn't actually become shorter, and
    #                           the shortening loop becomes infinite
    #
    # (The fix to the bug is, of course, to forget the object to be 
    # inserted before inserting it, thus removing duplicates in the MRU
    # list.)

    def test(self):
        context = obnam.context.Context()
        context.config.set("backup", "object-cache-size", "3")
        oc = obnam.io.ObjectCache(context)
        a = obnam.obj.Object("a", 0)
        b = obnam.obj.Object("b", 0)
        c = obnam.obj.Object("c", 0)
        d = obnam.obj.Object("d", 0)
        oc.put(a)
        oc.put(b)
        oc.put(c)
        oc.put(a)
        # If the bug is there, the next method call doesn't return.
        # Beware the operator.
        oc.put(b)


class LoadMapTests(IoBase):

    def test(self):
        map = obnam.map.create()
        obnam.map.add(map, "pink", "pretty")
        block_id = self.context.be.generate_block_id()
        block = obnam.map.encode_new_to_block(map, block_id)
        self.context.be.upload(block_id, block)
        
        obnam.io.load_maps(self.context, self.context.map, [block_id])
        self.failUnlessEqual(obnam.map.get(self.context.map, "pink"),
                             "pretty")
        self.failUnlessEqual(obnam.map.get(self.context.map, "black"),
                             None)
