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


"""Unit tests for obnamlib.io"""


import os
import shutil
import tempfile
import unittest


import obnamlib


class MockFadviseModule:

    def fadvise_dontneed(self, fd, pos, length):
        return -1


class MockLoggingModule:

    def warning(self, msg):
        pass


class ExceptionTests(unittest.TestCase):

    def testMissingBlock(self):
        e = obnamlib.io.MissingBlock("pink", "pretty")
        self.failUnless("pink" in str(e))
        self.failUnless("pretty" in str(e))

    def testFileContentsObjectMissing(self):
        e = obnamlib.io.FileContentsObjectMissing("pink")
        self.failUnless("pink" in str(e))


class ResolveTests(unittest.TestCase):

    def test(self):
        context = obnamlib.context.Context()
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
            x = obnamlib.io.resolve(context, pathname)
            self.failUnlessEqual(x, resolved)
            self.failUnlessEqual(obnamlib.io.unsolve(context, x), pathname)

        self.failUnlessEqual(obnamlib.io.unsolve(context, "/pink"), "pink")


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
    
        self.context = obnamlib.context.Context()
    
        for section, item, value in config_list:
            self.context.config.set(section, item, value)

        self.context.cache = obnamlib.Cache(self.context.config)
        self.context.be = obnamlib.backend.init(self.context.config, 
                                                self.context.cache)

    def tearDown(self):
        shutil.rmtree(self.cachedir)
        shutil.rmtree(self.rootdir)
        del self.cachedir
        del self.rootdir
        del self.context


class ObjectQueueFlushing(IoBase):

    def testEmptyQueue(self):
        obnamlib.io.flush_object_queue(self.context, self.context.oq, 
                                       self.context.map, False)
        list = self.context.be.list()
        self.failUnlessEqual(list, [])

    def testFlushing(self):
        self.context.oq.add("pink", "pretty")
        
        self.failUnlessEqual(self.context.be.list(), [])
        
        obnamlib.io.flush_object_queue(self.context, self.context.oq,
                                       self.context.map, False)

        list = self.context.be.list()
        self.failUnlessEqual(len(list), 1)
        
        b1 = os.path.basename(self.context.map["pink"])
        b2 = os.path.basename(list[0])
        self.failUnlessEqual(b1, b2)

    def testFlushAll(self):
        self.context.oq.add("pink", "pretty")
        self.context.content_oq.add("x", "y")
        obnamlib.io.flush_all_object_queues(self.context)
        self.failUnlessEqual(len(self.context.be.list()), 2)
        self.failUnless(self.context.oq.is_empty())
        self.failUnless(self.context.content_oq.is_empty())


class GetBlockTests(IoBase):
        
    def setup_pink_block(self, to_cache):
        self.context.be.upload_block("pink", "pretty", to_cache)

    def testRaisesIoErrorForNonExistentBlock(self):
        self.failUnlessRaises(IOError, obnamlib.io.get_block, self.context, "pink")
        
    def testFindsBlockWhenNotInCache(self):
        self.setup_pink_block(to_cache=False)
        self.failUnless(obnamlib.io.get_block(self.context, "pink"))
        
    def testFindsBlockWhenInCache(self):
        self.setup_pink_block(to_cache=True)
        obnamlib.io.get_block(self.context, "pink")
        self.failUnless(obnamlib.io.get_block(self.context, "pink"))


class GetObjectTests(IoBase):

    def upload_object(self, object_id, object):
        self.context.oq.add(object_id, object)
        obnamlib.io.flush_object_queue(self.context, self.context.oq,
                                       self.context.map, False)

    def testGetObject(self):
        id = "pink"
        component = obnamlib.cmp.Component(42, "pretty")
        object = obnamlib.obj.FilePartObject(id=id)
        object.add(component)
        object = object.encode()
        self.upload_object(id, object)
        o = obnamlib.io.get_object(self.context, id)

        self.failUnlessEqual(o.get_id(), id)
        self.failUnlessEqual(o.kind, obnamlib.obj.FILEPART)
        list = o.get_components()
        list = [c for c in list if c.kind not in [obnamlib.cmp.OBJID,
                                                        obnamlib.cmp.OBJKIND]]
        self.failUnlessEqual(len(list), 1)
        self.failUnlessEqual(list[0].kind, 42)
        self.failUnlessEqual(list[0].str, "pretty")

    def testGetObjectTwice(self):
        id = "pink"
        component = obnamlib.cmp.Component(42, "pretty")
        object = obnamlib.obj.FileListObject(id=id)
        object.add(component)
        object = object.encode()
        self.upload_object(id, object)
        o = obnamlib.io.get_object(self.context, id)
        o2 = obnamlib.io.get_object(self.context, id)
        self.failUnlessEqual(o, o2)

    def testReturnsNoneForNonexistentObject(self):
        self.failUnlessEqual(obnamlib.io.get_object(self.context, "pink"), None)


class HostBlock(IoBase):

    def testFetchHostBlock(self):
        host_id = self.context.config.get("backup", "host-id")
        host = obnamlib.obj.HostBlockObject(host_id=host_id, 
                                         gen_ids=["gen1", "gen2"],
                                         map_block_ids=["map1", "map2"], 
                                         contmap_block_ids=["contmap1", 
                                                            "contmap2"])
        host = host.encode()
        be = obnamlib.backend.init(self.context.config, self.context.cache)
        
        obnamlib.io.upload_host_block(self.context, host)
        host2 = obnamlib.io.get_host_block(self.context)
        self.failUnlessEqual(host, host2)

    def testFetchNonexistingHostBlockReturnsNone(self):
        self.failUnlessEqual(obnamlib.io.get_host_block(self.context), None)


class ObjectQueuingTests(unittest.TestCase):

    def find_block_files(self, config):
        files = []
        root = config.get("backup", "store")
        for dirpath, _, filenames in os.walk(root):
            files += [os.path.join(dirpath, x) for x in filenames]
        files.sort()
        return files

    def testEnqueue(self):
        context = obnamlib.context.Context()
        object_id = "pink"
        object = "pretty"
        context.config.set("backup", "block-size", "%d" % 128)
        context.cache = obnamlib.Cache(context.config)
        context.be = obnamlib.backend.init(context.config, context.cache)

        self.failUnlessEqual(self.find_block_files(context.config), [])
        
        obnamlib.io.enqueue_object(context, context.oq, context.map, 
                                   object_id, object, False)
        
        self.failUnlessEqual(self.find_block_files(context.config), [])
        self.failUnlessEqual(context.oq.combined_size(), len(object))
        
        object_id2 = "pink2"
        object2 = "x" * 1024

        obnamlib.io.enqueue_object(context, context.oq, context.map, 
                                   object_id2, object2, False)
        
        self.failUnlessEqual(len(self.find_block_files(context.config)), 1)
        self.failUnlessEqual(context.oq.combined_size(), len(object2))

        shutil.rmtree(context.config.get("backup", "cache"), True)
        shutil.rmtree(context.config.get("backup", "store"), True)


class FileContentsTests(unittest.TestCase):

    def setUp(self):
        self.context = obnamlib.context.Context()
        self.context.cache = obnamlib.Cache(self.context.config)
        self.context.be = obnamlib.backend.init(self.context.config, 
                                                self.context.cache)

    def tearDown(self):
        for x in ["cache", "store"]:
            if os.path.exists(self.context.config.get("backup", x)):
                shutil.rmtree(self.context.config.get("backup", x))

    def testEmptyFile(self):
        (fd, filename) = tempfile.mkstemp()
        os.close(fd)
        
        id = obnamlib.io.create_file_contents_object(self.context, filename)

        self.failIfEqual(id, None)
        self.failUnlessEqual(self.context.oq.ids(), [id])
        self.failUnlessEqual(len(self.context.map), 0)
            # there's no mapping yet, because the queue is small enough
            # that there has been no need to flush it

        os.remove(filename)

    def testNonEmptyFile(self):
        block_size = 4096
        self.context.config.set("backup", "block-size", "%d" % block_size)
        filename = "Makefile"
        
        mock_fadvise = MockFadviseModule()
        mock_logging = MockLoggingModule()
        id = obnamlib.io.create_file_contents_object(self.context, filename,
                                                     fadvise=mock_fadvise,
                                                     logging=mock_logging)

        self.failIfEqual(id, None)
        self.failUnlessEqual(self.context.oq.ids(), [id])

    def testRestore(self):
        block_size = 4096
        self.context.config.set("backup", "block-size", "%d" % block_size)
        filename = "Makefile"
        
        id = obnamlib.io.create_file_contents_object(self.context, filename)
        obnamlib.io.flush_object_queue(self.context, self.context.oq,
                                       self.context.map, False)
        obnamlib.io.flush_object_queue(self.context, self.context.content_oq,
                                       self.context.contmap, False)
        
        (fd, name) = tempfile.mkstemp()
        obnamlib.io.copy_file_contents(self.context, fd, id)
        os.close(fd)
        
        f = file(name, "r")
        data1 = f.read()
        f.close()
        os.remove(name)
        
        f = file(filename, "r")
        data2 = f.read()
        f.close()
        
        self.failUnlessEqual(data1, data2)

    def testRestoreNonexistingFile(self):
        self.failUnlessRaises(obnamlib.io.FileContentsObjectMissing,
                              obnamlib.io.copy_file_contents, self.context, None, "pink")


class MetaDataTests(unittest.TestCase):

    def testSet(self):
        (fd, name) = tempfile.mkstemp()
        os.close(fd)
        
        st1 = os.stat(name)
        inode = obnamlib.filelist.create_file_component_from_stat(name, st1, 
                                                               None, None,
                                                               None)

        os.chmod(name, 0)
        
        obnamlib.io.set_inode(name, inode)
        
        st2 = os.stat(name)
        
        self.failUnlessEqual(st1.st_mode, st2.st_mode)
        self.failUnlessEqual(st1.st_atime, st2.st_atime)
        self.failUnlessEqual(st1.st_mtime, st2.st_mtime)


class ObjectCacheTests(unittest.TestCase):

    def setUp(self):
        self.object = obnamlib.obj.FilePartObject(id="pink")
        self.object2 = obnamlib.obj.FilePartObject(id="pretty")
        self.object3 = obnamlib.obj.FilePartObject(id="beautiful")

    def testCreate(self):
        context = obnamlib.context.Context()
        oc = obnamlib.io.ObjectCache(context)
        self.failUnlessEqual(oc.size(), 0)
        self.failUnless(oc.MAX > 0)
        
    def testPut(self):
        context = obnamlib.context.Context()
        oc = obnamlib.io.ObjectCache(context)
        self.failUnlessEqual(oc.get("pink"), None)
        oc.put(self.object)
        self.failUnlessEqual(oc.get("pink"), self.object)

    def testPutWithOverflow(self):
        context = obnamlib.context.Context()
        oc = obnamlib.io.ObjectCache(context)
        oc.MAX = 1
        oc.put(self.object)
        self.failUnlessEqual(oc.size(), 1)
        self.failUnlessEqual(oc.get("pink"), self.object)
        oc.put(self.object2)
        self.failUnlessEqual(oc.size(), 1)
        self.failUnlessEqual(oc.get("pink"), None)
        self.failUnlessEqual(oc.get("pretty"), self.object2)

    def testPutWithOverflowPart2(self):
        context = obnamlib.context.Context()
        oc = obnamlib.io.ObjectCache(context)
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
        host = obnamlib.obj.HostBlockObject(host_id=host_id).encode()
        obnamlib.io.upload_host_block(self.context, host)
        
        list = obnamlib.io.find_reachable_data_blocks(self.context, host)
        self.failUnlessEqual(list, [])
        
        list2 = obnamlib.io.find_map_blocks_in_use(self.context, host, list)
        self.failUnlessEqual(list2, [])

    def testNoDataExtraMaps(self):
        self.context.map["pink"] = "pretty"
        map_block_id = "box"
        map_block = self.context.map.encode_new_to_block(map_block_id)
        self.context.be.upload_block(map_block_id, map_block, False)

        self.context.contmap["black"] = "beautiful"
        contmap_block_id = "fiddly"
        contmap_block = self.context.contmap.encode_new_to_block(
                            contmap_block_id)
        self.context.be.upload_block(contmap_block_id, contmap_block, False)

        host_id = self.context.config.get("backup", "host-id")
        host = obnamlib.obj.HostBlockObject(host_id=host_id, 
                                         map_block_ids=[map_block_id], 
                                         contmap_block_ids=[contmap_block_id])
        host = host.encode()
        obnamlib.io.upload_host_block(self.context, host)
        
        list = obnamlib.io.find_map_blocks_in_use(self.context, host, [])
        self.failUnlessEqual(list, [])

    def testDataAndMap(self):
        o = obnamlib.obj.FilePartObject(id="rouge")
        c = obnamlib.cmp.Component(obnamlib.cmp.FILECHUNK, "moulin")
        o.add(c)
        encoded_o = o.encode()
        
        block_id = "pink"
        oq = obnamlib.obj.ObjectQueue()
        oq.add("rouge", encoded_o)
        block = oq.as_block(block_id)
        self.context.be.upload_block(block_id, block, False)

        self.context.contmap["rouge"] = block_id
        map_block_id = "pretty"
        map_block = self.context.contmap.encode_new_to_block(map_block_id)
        self.context.be.upload_block(map_block_id, map_block, False)

        host_id = self.context.config.get("backup", "host-id")
        host = obnamlib.obj.HostBlockObject(host_id=host_id,
                                         map_block_ids=[map_block_id])
        host = host.encode()
        obnamlib.io.upload_host_block(self.context, host)
        
        list = obnamlib.io.find_map_blocks_in_use(self.context, host, 
                                                  [block_id])
        self.failUnlessEqual(list, [map_block_id])


class GarbageCollectionTests(IoBase):

    def testFindUnreachableFiles(self):
        host_id = self.context.config.get("backup", "host-id")
        host = obnamlib.obj.HostBlockObject(host_id=host_id).encode()
        obnamlib.io.upload_host_block(self.context, host)

        block_id = self.context.be.generate_block_id()
        self.context.be.upload_block(block_id, "pink", False)

        files = self.context.be.list()
        self.failUnlessEqual(files, [host_id, block_id])

        obnamlib.io.collect_garbage(self.context, host)
        files = self.context.be.list()
        self.failUnlessEqual(files, [host_id])


class ObjectCacheRegressionTest(unittest.TestCase):

    # This test case is for a bug in obnamlib.io.ObjectCache: with the
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
        context = obnamlib.context.Context()
        context.config.set("backup", "object-cache-size", "3")
        oc = obnamlib.io.ObjectCache(context)
        a = obnamlib.obj.FilePartObject(id="a")
        b = obnamlib.obj.FilePartObject(id="b")
        c = obnamlib.obj.FilePartObject(id="c")
        d = obnamlib.obj.FilePartObject(id="d")
        oc.put(a)
        oc.put(b)
        oc.put(c)
        oc.put(a)
        # If the bug is there, the next method call doesn't return.
        # Beware the operator.
        oc.put(b)

