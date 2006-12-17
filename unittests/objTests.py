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
        self.failUnlessEqual(kind_name(INODE), "INODE")
        self.failUnlessEqual(kind_name(GEN), "GEN")
        self.failUnlessEqual(kind_name(SIG), "SIG")
        self.failUnlessEqual(kind_name(HOST), "HOST")
        self.failUnlessEqual(kind_name(FILECONTENTS), "FILECONTENTS")
        self.failUnlessEqual(kind_name(FILELIST), "FILELIST")
        self.failUnlessEqual(kind_name(DELTA), "DELTA")


class ObjectCreateTests(unittest.TestCase):

    def testCreate(self):
        o = obnam.obj.create("pink", 1)
        self.failUnlessEqual(obnam.obj.get_id(o), "pink")
        self.failUnlessEqual(obnam.obj.get_kind(o), 1)
        self.failUnlessEqual(obnam.obj.get_components(o), [])

    def testAdd(self):
        o = obnam.obj.create("pink", 1)
        c = obnam.cmp.create(2, "pretty")
        obnam.obj.add(o, c)
        self.failUnlessEqual(obnam.obj.get_components(o), [c])


class ObjectEncodingDecodingTests(unittest.TestCase):

    def test(self):
        c1 = obnam.cmp.create(0xdeadbeef, "hello")
        c2 = obnam.cmp.create(0xcafebabe, "world")
        o = obnam.obj.create("uuid", 0xdada)
        obnam.obj.add(o, c1)
        obnam.obj.add(o, c2)
        
        encoded = obnam.obj.encode(o)
        o2 = obnam.obj.decode(encoded, 0)
        encoded2 = obnam.obj.encode(o2)
        
        self.failUnlessEqual(encoded, encoded2)
        return
        
        self.failUnlessEqual(len(components), 4) # id, kind, cmpnt1, cmpnt2
        
        self.failUnlessEqual(components[0], 
                             (obnam.cmp.OBJID, "uuid"))
        self.failUnlessEqual(components[1], 
                             (obnam.cmp.OBJKIND, 0xdada))
        self.failUnlessEqual(components[2], (0xdeadbeef, "hello"))
        self.failUnlessEqual(components[3], (0xcafebabe, "world"))


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
        o = obnam.obj.create("pink", 1)
        obnam.obj.add(o, obnam.cmp.create(2, "pretty"))
        oq = queue_create()
        queue_add(oq, "pink", obnam.obj.encode(o))
        block = block_create_from_object_queue("blkid", oq)

        list = obnam.obj.block_decode(block)
        self.failUnlessEqual(
            obnam.cmp.first_string_by_kind(list, obnam.cmp.BLKID),
            "blkid")
        self.failUnlessEqual(len(list), 2)
        o2 = obnam.cmp.first_by_kind(list, obnam.cmp.OBJECT)
        self.failUnlessEqual(obnam.obj.first_string_by_kind(o, 2), 
                             "pretty")
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
        self.failUnlessEqual(obnam.obj.get_id(o), "pink")
        self.failUnlessEqual(obnam.obj.get_kind(o), obnam.obj.SIG)
        self.failUnlessEqual(len(obnam.obj.get_components(o)), 1)
        self.failUnlessEqual(
            obnam.obj.first_string_by_kind(o, obnam.cmp.SIGDATA),
            sig)

    def testCreateDeltaObject(self):
        id = "pink"
        delta = "xyzzy"
        encoded = delta_object_encode(id, delta, "pretty", None)
        o = obnam.obj.decode(encoded, 0)
        self.failUnlessEqual(obnam.obj.get_id(o), "pink")
        self.failUnlessEqual(obnam.obj.get_kind(o), obnam.obj.DELTA)
        self.failUnlessEqual(len(obnam.obj.get_components(o)), 2)
        self.failUnlessEqual(
            obnam.obj.first_string_by_kind(o, obnam.cmp.DELTADATA),
            delta)
        self.failUnlessEqual(
            obnam.obj.first_string_by_kind(o, obnam.cmp.CONTREF),
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
        subs = obnam.cmp.get_subcomponents(c)
        id = obnam.cmp.first_string_by_kind(subs, obnam.cmp.OBJID)
        self.failUnlessEqual(id, "pink")
        ver = obnam.cmp.first_string_by_kind(subs, 
                                            obnam.cmp.FORMATVERSION)
        self.failUnlessEqual(ver, "1")


class GetComponentTests(unittest.TestCase):

    def setUp(self):
        self.o = obnam.obj.create("uuid", 0)
        obnam.obj.add(self.o, obnam.cmp.create(1, "pink"))
        obnam.obj.add(self.o, obnam.cmp.create(2, "pretty"))
        obnam.obj.add(self.o, obnam.cmp.create(3, "red"))
        obnam.obj.add(self.o, obnam.cmp.create(3, "too"))

    def testGetByKind(self):
        find = lambda t: \
            [obnam.cmp.get_string_value(c) 
                for c in obnam.obj.find_by_kind(self.o, t)]
        self.failUnlessEqual(find(1), ["pink"])
        self.failUnlessEqual(find(2), ["pretty"])
        self.failUnlessEqual(find(3), ["red", "too"])
        self.failUnlessEqual(find(0), [])

    def testGetStringsByKind(self):
        find = lambda t: obnam.obj.find_strings_by_kind(self.o, t)
        self.failUnlessEqual(find(1), ["pink"])
        self.failUnlessEqual(find(2), ["pretty"])
        self.failUnlessEqual(find(3), ["red", "too"])
        self.failUnlessEqual(find(0), [])

    def helper(self, wanted_kind):
        c = obnam.obj.first_by_kind(self.o, wanted_kind)
        if c:
            return obnam.cmp.get_string_value(c)
        else:
            return None

    def testGetFirstByKind(self):
        self.failUnlessEqual(self.helper(1), "pink")
        self.failUnlessEqual(self.helper(2), "pretty")
        self.failUnlessEqual(self.helper(3), "red")
        self.failUnlessEqual(self.helper(0), None)

    def testGetFirstStringByKind(self):
        find = lambda t: obnam.obj.first_string_by_kind(self.o, t)
        self.failUnlessEqual(find(1), "pink")
        self.failUnlessEqual(find(2), "pretty")
        self.failUnlessEqual(find(3), "red")
        self.failUnlessEqual(find(0), None)

    def testGetVarintsByKind(self):
        list = range(1024)

        o = obnam.obj.create("uuid", 0)
        for i in list:
            c = obnam.cmp.create(0, obnam.varint.encode(i))
            obnam.obj.add(o, c)

        self.failUnlessEqual(obnam.obj.find_varints_by_kind(o, 0), list)

    def testGetFirstSVarintByKind(self):
        o = obnam.obj.create("uuid", 0)
        for i in range(1024):
            c = obnam.cmp.create(i, obnam.varint.encode(i))
            obnam.obj.add(o, c)

        for i in range(1024):
            self.failUnlessEqual(obnam.obj.first_varint_by_kind(o, i), i)
