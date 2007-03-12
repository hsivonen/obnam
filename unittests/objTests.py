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


class ObjectCreateTests(unittest.TestCase):

    def testCreate(self):
        o = obnam.obj.Object("pink", 1)
        self.failUnlessEqual(o.get_id(), "pink")
        self.failUnlessEqual(o.get_kind(), 1)
        self.failUnlessEqual(o.get_components(), [])

    def testAdd(self):
        o = obnam.obj.Object("pink", 1)
        c = obnam.cmp.Component(2, "pretty")
        o.add(c)
        self.failUnlessEqual(o.get_components(), [c])


class ObjectEncodingDecodingTests(unittest.TestCase):

    def test(self):
        c1 = obnam.cmp.Component(0xdeadbeef, "hello")
        c2 = obnam.cmp.Component(0xcafebabe, "world")
        o = obnam.obj.Object("uuid", 0xdada)
        o.add(c1)
        o.add(c2)
        
        encoded = obnam.obj.encode(o)
        o2 = obnam.obj.decode(encoded, 0)
        encoded2 = obnam.obj.encode(o2)
        
        self.failUnlessEqual(encoded, encoded2)


class ObjectQueueTests(unittest.TestCase):

    def testCreate(self):
        oq = queue_create()
        self.failUnlessEqual(queue_combined_size(oq), 0)

    def testAdd(self):
        oq = queue_create()
        queue_add(oq, "xx", "abc")
        self.failUnlessEqual(queue_combined_size(oq), 3)

    def testSize(self):
        oq = queue_create()
        self.failUnless(queue_is_empty(oq))
        queue_add(oq, "xx", "abc")
        self.failUnlessEqual(queue_combined_size(oq), 3)
        queue_add(oq, "yy", "abc")
        self.failUnlessEqual(queue_combined_size(oq), 6)

    def testClear(self):
        oq = queue_create()
        oq_orig = oq
        self.failUnless(queue_is_empty(oq))
        queue_clear(oq)
        self.failUnlessEqual(queue_combined_size(oq), 0)
        queue_add(oq, "xx", "abc")
        self.failUnlessEqual(queue_combined_size(oq), 3)
        queue_clear(oq)
        self.failUnless(queue_is_empty(oq))
        self.failUnless(oq == oq_orig)


class BlockCreateTests(unittest.TestCase):

    def testDecodeInvalidObject(self):
        self.failUnlessEqual(obnam.obj.block_decode("pink"), None)

    def testEmptyObjectQueue(self):
        oq = queue_create()
        block = block_create_from_object_queue("blkid", oq)
        list = obnam.obj.block_decode(block)
        self.failUnlessEqual(
            obnam.cmp.first_string_by_kind(list, obnam.cmp.BLKID),
            "blkid")
        self.failUnlessEqual(len(list), 1)
        self.failUnlessEqual(queue_ids(oq), [])

    def testObjectQueue(self):
        o = obnam.obj.Object("pink", 1)
        o.add(obnam.cmp.Component(2, "pretty"))
        oq = queue_create()
        queue_add(oq, "pink", obnam.obj.encode(o))
        block = block_create_from_object_queue("blkid", oq)

        list = obnam.obj.block_decode(block)
        self.failUnlessEqual(
            obnam.cmp.first_string_by_kind(list, obnam.cmp.BLKID),
            "blkid")
        self.failUnlessEqual(len(list), 2)
        o2 = obnam.cmp.first_by_kind(list, obnam.cmp.OBJECT)
        self.failUnlessEqual(o.first_string_by_kind(2), "pretty")
        self.failUnlessEqual(queue_ids(oq), ["pink"])


class GenerationTests(unittest.TestCase):

    def testEncodeDecode(self):
        id1 = "pink"
        fl1 = "pretty"
        start1 = 12765
        end1 = 37337
        gen = generation_object_encode(id1, fl1, start1, end1)
        (id2, fl2, start2, end2) = generation_object_decode(gen)
        self.failUnlessEqual(id1, id2)
        self.failUnlessEqual(fl1, fl2)
        self.failUnlessEqual(start1, start2)
        self.failUnlessEqual(end1, end2)


class ObjectTests(unittest.TestCase):

    def testId(self):
        id = obnam.obj.object_id_new()
        self.failIfEqual(id, None)
        self.failUnlessEqual(type(id), type(""))

    def testCreateSignatureObject(self):
        context = obnam.context.create()
        id = "pink"
        sig = obnam.rsync.compute_signature(context, "Makefile")
        encoded = signature_object_encode(id, sig)
        o = obnam.obj.decode(encoded, 0)
        self.failUnlessEqual(o.get_id(), "pink")
        self.failUnlessEqual(o.get_kind(), obnam.obj.SIG)
        self.failUnlessEqual(len(o.get_components()), 1)
        self.failUnlessEqual(o.first_string_by_kind(obnam.cmp.SIGDATA), sig)

    def testCreateDeltaObjectWithContRef(self):
        id = "pink"
        deltapart_ref = "xyzzy"
        encoded = delta_object_encode(id, [deltapart_ref], "pretty", None)
        o = obnam.obj.decode(encoded, 0)
        self.failUnlessEqual(o.get_id(), "pink")
        self.failUnlessEqual(o.get_kind(), obnam.obj.DELTA)
        self.failUnlessEqual(len(o.get_components()), 2)
        self.failUnlessEqual(o.first_string_by_kind(obnam.cmp.DELTAPARTREF),
                             deltapart_ref)
        self.failUnlessEqual(o.first_string_by_kind(obnam.cmp.CONTREF),
                             "pretty")

    def testCreateDeltaObjectWithDeltaRef(self):
        id = "pink"
        deltapart_ref = "xyzzy"
        encoded = delta_object_encode(id, [deltapart_ref], None, "pretty")
        o = obnam.obj.decode(encoded, 0)
        self.failUnlessEqual(o.get_id(), "pink")
        self.failUnlessEqual(o.get_kind(), obnam.obj.DELTA)
        self.failUnlessEqual(len(o.get_components()), 2)
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
        host = obnam.obj.host_block_encode(host_id, gen_ids, map_ids, 
                                              contmap_ids)
        self.failUnless(host.startswith(obnam.obj.BLOCK_COOKIE))
        (host_id2, gen_ids2, map_ids2, contmap_ids2) = \
            obnam.obj.host_block_decode(host)
        self.failUnlessEqual(host_id, host_id2)
        self.failUnlessEqual(gen_ids, gen_ids2)
        self.failUnlessEqual(map_ids, map_ids2)
        self.failUnlessEqual(contmap_ids, contmap_ids2)
        
    def testFormatVersion(self):
        encoded = obnam.obj.host_block_encode("pink", [], [], [])
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
        self.o = obnam.obj.Object("uuid", 0)
        self.o.add(obnam.cmp.Component(1, "pink"))
        self.o.add(obnam.cmp.Component(2, "pretty"))
        self.o.add(obnam.cmp.Component(3, "red"))
        self.o.add(obnam.cmp.Component(3, "too"))

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
        list = range(1024)

        o = obnam.obj.Object("uuid", 0)
        for i in list:
            c = obnam.cmp.Component(0, obnam.varint.encode(i))
            o.add(c)

        self.failUnlessEqual(o.find_varints_by_kind(0), list)

    def testGetFirstSVarintByKind(self):
        o = obnam.obj.Object("uuid", 0)
        for i in range(1024):
            c = obnam.cmp.Component(i, obnam.varint.encode(i))
            o.add(c)

        for i in range(1024):
            self.failUnlessEqual(o.first_varint_by_kind(i), i)
        self.failUnlessEqual(o.first_varint_by_kind(-1), None)
