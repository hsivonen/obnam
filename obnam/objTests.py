# Copyright (C) 2006, 2007, 2008  Lars Wirzenius <liw@iki.fi>
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


"""Unit tests for obnam.obj."""


import os
import unittest


from obnam.obj import *
import obnam


class ObjectKindNameTests(unittest.TestCase):

    def test(self):
        self.failUnlessEqual(kind_name(-12765), "UNKNOWN")
        self.failUnlessEqual(kind_name(FILEPART), "FILEPART")
        self.failUnlessEqual(kind_name(GEN), "GEN")
        self.failUnlessEqual(kind_name(SIG), "SIG")
        self.failUnlessEqual(kind_name(HOST), "HOST")
        self.failUnlessEqual(kind_name(FILECONTENTS), "FILECONTENTS")
        self.failUnlessEqual(kind_name(FILELIST), "FILELIST")
        self.failUnlessEqual(kind_name(DELTA), "DELTA")
        self.failUnlessEqual(kind_name(DELTAPART), "DELTAPART")
        self.failUnlessEqual(kind_name(DIR), "DIR")
        self.failUnlessEqual(kind_name(FILEGROUP), "FILEGROUP")


class ObjectIdTests(unittest.TestCase):

    def testHasCorrectProperties(self):
        id = obnam.obj.object_id_new()
        self.failUnlessEqual(type(id), type(""))


class StorageObjectTests(unittest.TestCase):

    components = [
        obnam.cmp.Component(obnam.cmp.OBJID, "pink"),
        obnam.cmp.Component(obnam.cmp.OBJKIND, 
                            obnam.varint.encode(obnam.obj.HOST)),
        obnam.cmp.Component(0xdeadbeef, "hello"),
        obnam.cmp.Component(0xcafebabe, "world"),
    ]
    
    def setUp(self):
        self.o = obnam.obj.StorageObject(components=self.components)

    def testInitializesComponentListCorrectlyFromComponents(self):
        self.failUnlessEqual(len(self.o.get_components()),
                             len(self.components))

    def testInitalizesIdCorrectlyFromComponents(self):
        self.failUnlessEqual(self.o.get_id(), "pink")

    def testInitalizesKindCorrectlyFromComponents(self):
        self.failUnlessEqual(self.o.get_kind(), obnam.obj.HOST)

    def testInitializesIdCorrectlyFromArguments(self):
        o = obnam.obj.StorageObject(id="pink")
        self.failUnlessEqual(o.get_id(), "pink")

    def testEncodesAndDecodesToIdenticalObject(self):
        o = obnam.obj.StorageObject(components=self.components)
        encoded = o.encode()
        o2 = obnam.obj.decode(encoded)
        encoded2 = o2.encode()
        self.failUnlessEqual(encoded, encoded2)

    def testAddsComponentCorrectly(self):
        c = obnam.cmp.Component(obnam.cmp.FILENAME, "pretty")
        self.o.add(c)
        self.failUnless(self.o.find_by_kind(obnam.cmp.FILENAME), [c])


class ObjectQueueTests(unittest.TestCase):

    def testCreate(self):
        oq = obnam.obj.ObjectQueue()
        self.failUnlessEqual(oq.combined_size(), 0)

    def testAdd(self):
        oq = obnam.obj.ObjectQueue()
        oq.add("xx", "abc")
        self.failUnlessEqual(oq.combined_size(), 3)

    def testSize(self):
        oq = obnam.obj.ObjectQueue()
        self.failUnless(oq.is_empty())
        oq.add("xx", "abc")
        self.failUnlessEqual(oq.combined_size(), 3)
        oq.add("yy", "abc")
        self.failUnlessEqual(oq.combined_size(), 6)

    def testClear(self):
        oq = obnam.obj.ObjectQueue()
        oq_orig = oq
        self.failUnless(oq.is_empty())
        oq.clear()
        self.failUnlessEqual(oq.combined_size(), 0)
        oq.add("xx", "abc")
        self.failUnlessEqual(oq.combined_size(), 3)
        oq.clear()
        self.failUnless(oq.is_empty())
        self.failUnless(oq == oq_orig)


class BlockWithoutCookieTests(unittest.TestCase):

    def setUp(self):
        self.e = obnam.obj.BlockWithoutCookie("\x01\x02\x03")

    def testIncludesBlockHexDumpInMessage(self):
        self.failUnless("01 02 03" in str(self.e))


class BlockCreateTests(unittest.TestCase):

    def testDecodeInvalidObject(self):
        self.failUnlessRaises(obnam.obj.BlockWithoutCookie,
                              obnam.obj.block_decode, "pink")

    def testEmptyObjectQueue(self):
        oq = obnam.obj.ObjectQueue()
        block = oq.as_block("blkid")
        list = obnam.obj.block_decode(block)
        self.failUnlessEqual(
            obnam.cmp.first_string_by_kind(list, obnam.cmp.BLKID),
            "blkid")
        self.failUnlessEqual(len(list), 1)
        self.failUnlessEqual(oq.ids(), [])

    def testObjectQueue(self):
        o = obnam.obj.StorageObject(id="pink")
        o.add(obnam.cmp.Component(2, "pretty"))
        oq = obnam.obj.ObjectQueue()
        oq.add("pink", o.encode())
        block = oq.as_block("blkid")

        list = obnam.obj.block_decode(block)
        self.failUnlessEqual(
            obnam.cmp.first_string_by_kind(list, obnam.cmp.BLKID),
            "blkid")
        self.failUnlessEqual(len(list), 2)
        o2 = obnam.cmp.first_by_kind(list, obnam.cmp.OBJECT)
        self.failUnlessEqual(o.first_string_by_kind(2), "pretty")
        self.failUnlessEqual(oq.ids(), ["pink"])


class GenerationTests(unittest.TestCase):

    def testEncodeDecode(self):
        id1 = "pink"
        fl1 = "pretty"
        dirs1 = ["dir1", "dir2"]
        fg1 = ["fg1", "fg2"]
        start1 = 12765
        end1 = 37337
        gen = obnam.obj.GenerationObject(id=id1, filelist_id=fl1, 
                                         dirrefs=dirs1, filegrouprefs=fg1, 
                                         start=start1, end=end1).encode()
        (id2, fl2, dirs2, fg2, start2, end2) = generation_object_decode(gen)
        self.failUnlessEqual(id1, id2)
        self.failUnlessEqual(fl1, fl2)
        self.failUnlessEqual(dirs1, dirs2)
        self.failUnlessEqual(fg1, fg2)
        self.failUnlessEqual(start1, start2)
        self.failUnlessEqual(end1, end2)

    def setUp(self):
        self.gen = GenerationObject(id="objid", filelist_id="filelistref", 
                                    dirrefs=["dir2", "dir1"], 
                                    filegrouprefs=["fg2", "fg1"],
                                    start=123, end=456)

    def testSetsFilelistRefCorrectly(self):
        self.failUnlessEqual(self.gen.get_filelistref(), "filelistref")

    def testSetsDirRefsCorrectly(self):
        self.failUnlessEqual(sorted(self.gen.get_dirrefs()), 
                             sorted(["dir1", "dir2"]))

    def testSetsFileGroupRefsCorrectly(self):
        self.failUnlessEqual(sorted(self.gen.get_filegrouprefs()), 
                             sorted(["fg1", "fg2"]))

    def testSetsStartTimeCorrectly(self):
        self.failUnlessEqual(self.gen.get_start_time(), 123)

    def testSetsEndTimeCorrectly(self):
        self.failUnlessEqual(self.gen.get_end_time(), 456)


class OldStorageObjectTests(unittest.TestCase):

    def testCreateSignatureObject(self):
        context = obnam.context.Context()
        id = "pink"
        sig = obnam.rsync.compute_signature(context, "Makefile")
        sig_object = obnam.obj.SignatureObject(id=id, sigdata=sig)
        encoded = sig_object.encode()
        o = obnam.obj.decode(encoded)
        self.failUnlessEqual(o.get_id(), "pink")
        self.failUnlessEqual(o.get_kind(), obnam.obj.SIG)
        self.failUnlessEqual(len(o.get_components()), 1+2)
        self.failUnlessEqual(o.first_string_by_kind(obnam.cmp.SIGDATA), sig)

    def testCreateDeltaObjectWithContRef(self):
        id = "pink"
        deltapart_ref = "xyzzy"
        do = obnam.obj.DeltaObject(id=id, deltapart_refs=[deltapart_ref], 
                                   cont_ref="pretty")
        encoded = do.encode()
        o = obnam.obj.decode(encoded)
        self.failUnlessEqual(o.get_id(), "pink")
        self.failUnlessEqual(o.get_kind(), obnam.obj.DELTA)
        self.failUnlessEqual(len(o.get_components()), 2+2)
        self.failUnlessEqual(o.first_string_by_kind(obnam.cmp.DELTAPARTREF),
                             deltapart_ref)
        self.failUnlessEqual(o.first_string_by_kind(obnam.cmp.CONTREF),
                             "pretty")

    def testCreateDeltaObjectWithDeltaRef(self):
        id = "pink"
        deltapart_ref = "xyzzy"
        do = obnam.obj.DeltaObject(id=id, deltapart_refs=[deltapart_ref], 
                                   delta_ref="pretty")
        encoded = do.encode()
        o = obnam.obj.decode(encoded)
        self.failUnlessEqual(o.get_id(), "pink")
        self.failUnlessEqual(o.get_kind(), obnam.obj.DELTA)
        self.failUnlessEqual(len(o.get_components()), 2+2)
        self.failUnlessEqual(o.first_string_by_kind(obnam.cmp.DELTAPARTREF),
                             deltapart_ref)
        self.failUnlessEqual(o.first_string_by_kind(obnam.cmp.DELTAREF),
                             "pretty")


class HostBlockTests(unittest.TestCase):

    def testEncodeDecode(self):
        host_id = "pink"
        gen_ids = ["pretty", "beautiful"]
        map_ids = ["black", "box"]
        contmap_ids = ["tilu", "lii"]
        host = obnam.obj.HostBlockObject(host_id=host_id, gen_ids=gen_ids, 
                                         map_block_ids=map_ids, 
                                         contmap_block_ids=contmap_ids)
        host = host.encode()
        self.failUnless(host.startswith(obnam.obj.BLOCK_COOKIE))
        (host_id2, gen_ids2, map_ids2, contmap_ids2) = \
            obnam.obj.host_block_decode(host)
        self.failUnlessEqual(host_id, host_id2)
        self.failUnlessEqual(gen_ids, gen_ids2)
        self.failUnlessEqual(map_ids, map_ids2)
        self.failUnlessEqual(contmap_ids, contmap_ids2)
        
    def testFormatVersion(self):
        encoded = obnam.obj.HostBlockObject(host_id="pink", gen_ids=[], 
                                            map_block_ids=[], 
                                            contmap_block_ids=[]).encode()
        decoded = obnam.obj.block_decode(encoded)
        c = obnam.cmp.first_by_kind(decoded, obnam.cmp.OBJECT)
        subs = c.get_subcomponents()
        id = obnam.cmp.first_string_by_kind(subs, obnam.cmp.OBJID)
        self.failUnlessEqual(id, "pink")
        ver = obnam.cmp.first_string_by_kind(subs, 
                                            obnam.cmp.FORMATVERSION)
        self.failUnlessEqual(ver, "1")


class GetComponentTests(unittest.TestCase):

    def setUp(self):
        self.o = obnam.obj.StorageObject([
            obnam.cmp.Component(1, "pink"),
            obnam.cmp.Component(2, "pretty"),
            obnam.cmp.Component(3, "red"),
            obnam.cmp.Component(3, "too"),
            ])

    def testGetByKind(self):
        find = lambda t: \
            [c.get_string_value() for c in self.o.find_by_kind(t)]
        self.failUnlessEqual(find(1), ["pink"])
        self.failUnlessEqual(find(2), ["pretty"])
        self.failUnlessEqual(find(3), ["red", "too"])
        self.failUnlessEqual(find(0), [])

    def testGetStringsByKind(self):
        find = lambda t: self.o.find_strings_by_kind(t)
        self.failUnlessEqual(find(1), ["pink"])
        self.failUnlessEqual(find(2), ["pretty"])
        self.failUnlessEqual(find(3), ["red", "too"])
        self.failUnlessEqual(find(0), [])

    def helper(self, wanted_kind):
        c = self.o.first_by_kind(wanted_kind)
        if c:
            return c.get_string_value()
        else:
            return None

    def testGetFirstByKind(self):
        self.failUnlessEqual(self.helper(1), "pink")
        self.failUnlessEqual(self.helper(2), "pretty")
        self.failUnlessEqual(self.helper(3), "red")
        self.failUnlessEqual(self.helper(0), None)

    def testGetFirstStringByKind(self):
        find = lambda t: self.o.first_string_by_kind(t)
        self.failUnlessEqual(find(1), "pink")
        self.failUnlessEqual(find(2), "pretty")
        self.failUnlessEqual(find(3), "red")
        self.failUnlessEqual(find(0), None)

    def testGetVarintsByKind(self):
        numbers = range(1024)
        components = [obnam.cmp.Component(0, obnam.varint.encode(i))
                      for i in numbers]
        o = obnam.obj.StorageObject(components=components)
        self.failUnlessEqual(o.find_varints_by_kind(0), numbers)

    def testGetFirstSVarintByKind(self):
        numbers = range(0, 1024, 17)
        components = [obnam.cmp.Component(i, obnam.varint.encode(i))
                      for i in numbers]
        o = obnam.obj.StorageObject(components=components)
        for i in numbers:
            self.failUnlessEqual(o.first_varint_by_kind(i), i)
        self.failUnlessEqual(o.first_varint_by_kind(-1), None)


class DirObjectTests(unittest.TestCase):

    def setUp(self):
        self.stat = os.stat(".")
        self.dir = DirObject(id="pink", name="name", stat=self.stat, 
                             dirrefs=["dir2", "dir1"], 
                             filegrouprefs=["fg2", "fg1"])

    def testSetsNameCorrectly(self):
        self.failUnlessEqual(self.dir.get_name(), "name")

    def testSetsStatCorrectly(self):
        self.failUnlessEqual(self.dir.get_stat(), self.stat)

    def testSetsDirrefsCorrectly(self):
        self.failUnlessEqual(sorted(self.dir.get_dirrefs()), 
                             sorted(["dir1", "dir2"]))

    def testSetsFilegrouprefsCorrectly(self):
        self.failUnlessEqual(sorted(self.dir.get_filegrouprefs()), 
                             sorted(["fg1", "fg2"]))


class FileGroupObjectTests(unittest.TestCase):

    def setUp(self):
        stat = os.stat("README")
        self.files = [
            ("pink", stat, "pink_contref", "pink_sigref", None),
            ("pretty", stat, None, "pretty_sigref", "pretty_deltaref"),
            ("black", stat, "black_contref", "black_sigref", None),
        ]
        self.names = [x[0] for x in self.files]
        self.fg = FileGroupObject(id="objid")
        for name, stat, contref, sigref, deltaref in self.files:
            self.fg.add_file(name, stat, contref, sigref, deltaref)

    def testReturnsNoneIfSoughtFileNotFound(self):
        self.failUnlessEqual(self.fg.get_file("xxx"), None)
        
    def testSetsNamesCorrectly(self):
        self.failUnlessEqual(sorted(self.fg.get_names()), sorted(self.names))

    def testSetsStatCorrectly(self):
        for x in self.files:
            self.failUnlessEqual(x[1], self.fg.get_stat(x[0]))

    def testSetsContentRefCorrectly(self):
        for x in self.files:
            self.failUnlessEqual(x[2], self.fg.get_contref(x[0]))

    def testSetsSigRefCorrectly(self):
        for x in self.files:
            self.failUnlessEqual(x[3], self.fg.get_sigref(x[0]))

    def testSetsDeltaRefCorrectly(self):
        for x in self.files:
            self.failUnlessEqual(x[4], self.fg.get_deltaref(x[0]))


class StorageObjectFactoryTests(unittest.TestCase):

    def setUp(self):
        self.factory = StorageObjectFactory()

    def make_component(self, objkind):
        list = []
        
        list.append(obnam.cmp.Component(obnam.cmp.OBJID, "objid"))
        list.append(obnam.cmp.Component(obnam.cmp.OBJKIND, 
                                        obnam.varint.encode(objkind)))
        
        return list

    def make_object(self, objkind):
        return self.factory.get_object(self.make_component(objkind))

    def testCreatesSignatureObjectCorrectly(self):
        o = self.make_object(obnam.obj.SIG)
        self.failUnlessEqual(type(o), obnam.obj.SignatureObject)
