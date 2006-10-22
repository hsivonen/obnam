"""Unit tests for wibbrlib.obj."""


import os
import unittest


from wibbrlib.obj import *
import wibbrlib


class ObjectKindNameTests(unittest.TestCase):

    def test(self):
        self.failUnlessEqual(kind_name(-12765), "OBJ_UNKNOWN")
        self.failUnlessEqual(kind_name(OBJ_FILEPART), "OBJ_FILEPART")
        self.failUnlessEqual(kind_name(OBJ_INODE), "OBJ_INODE")
        self.failUnlessEqual(kind_name(OBJ_GEN), "OBJ_GEN")
        self.failUnlessEqual(kind_name(OBJ_SIG), "OBJ_SIG")
        self.failUnlessEqual(kind_name(OBJ_HOST), "OBJ_HOST")


class ObjectCreateTests(unittest.TestCase):

    def testCreate(self):
        o = wibbrlib.obj.create("pink", 1)
        self.failUnlessEqual(wibbrlib.obj.get_id(o), "pink")
        self.failUnlessEqual(wibbrlib.obj.get_kind(o), 1)
        self.failUnlessEqual(wibbrlib.obj.get_components(o), [])

    def testAdd(self):
        o = wibbrlib.obj.create("pink", 1)
        c = wibbrlib.cmp.create(2, "pretty")
        wibbrlib.obj.add(o, c)
        self.failUnlessEqual(wibbrlib.obj.get_components(o), [c])


class ObjectEncodingDecodingTests(unittest.TestCase):

    def test(self):
        c1 = wibbrlib.cmp.create(0xdeadbeef, "hello")
        c2 = wibbrlib.cmp.create(0xcafebabe, "world")
        o = wibbrlib.obj.create("uuid", 0xdada)
        wibbrlib.obj.add(o, c1)
        wibbrlib.obj.add(o, c2)
        
        encoded = wibbrlib.obj.encode(o)
        o2 = wibbrlib.obj.decode(encoded, 0)
        encoded2 = wibbrlib.obj.encode(o2)
        
        self.failUnlessEqual(encoded, encoded2)
        return
        
        self.failUnlessEqual(len(components), 4) # id, kind, cmpnt1, cmpnt2
        
        self.failUnlessEqual(components[0], 
                             (wibbrlib.cmp.CMP_OBJID, "uuid"))
        self.failUnlessEqual(components[1], 
                             (wibbrlib.cmp.CMP_OBJKIND, 0xdada))
        self.failUnlessEqual(components[2], (0xdeadbeef, "hello"))
        self.failUnlessEqual(components[3], (0xcafebabe, "world"))


class ObjectQueueTests(unittest.TestCase):

    def testCreate(self):
        self.failUnlessEqual(object_queue_create(), [])

    def testAdd(self):
        oq = object_queue_create()
        object_queue_add(oq, "xx", "abc")
        self.failUnlessEqual(oq, [("xx", "abc")])

    def testSize(self):
        oq = object_queue_create()
        self.failUnlessEqual(object_queue_combined_size(oq), 0)
        object_queue_add(oq, "xx", "abc")
        self.failUnlessEqual(object_queue_combined_size(oq), 3)
        object_queue_add(oq, "yy", "abc")
        self.failUnlessEqual(object_queue_combined_size(oq), 6)

    def testClear(self):
        oq = object_queue_create()
        oq_orig = oq
        self.failUnlessEqual(object_queue_combined_size(oq), 0)
        object_queue_clear(oq)
        self.failUnlessEqual(object_queue_combined_size(oq), 0)
        object_queue_add(oq, "xx", "abc")
        self.failUnlessEqual(object_queue_combined_size(oq), 3)
        object_queue_clear(oq)
        self.failUnlessEqual(object_queue_combined_size(oq), 0)
        self.failUnless(oq == oq_orig)


class BlockCreateTests(unittest.TestCase):

    def testEmptyObjectQueue(self):
        oq = object_queue_create()
        block = block_create_from_object_queue("blkid", oq)
        list = wibbrlib.obj.block_decode(block)
        self.failUnlessEqual(
            wibbrlib.cmp.first_string_by_kind(list, wibbrlib.cmp.CMP_BLKID),
            "blkid")
        self.failUnlessEqual(len(list), 1)
        self.failUnlessEqual(object_queue_ids(oq), [])

    def testObjectQueue(self):
        o = wibbrlib.obj.create("pink", 1)
        wibbrlib.obj.add(o, wibbrlib.cmp.create(2, "pretty"))
        oq = object_queue_create()
        object_queue_add(oq, "pink", wibbrlib.obj.encode(o))
        block = block_create_from_object_queue("blkid", oq)

        list = wibbrlib.obj.block_decode(block)
        self.failUnlessEqual(
            wibbrlib.cmp.first_string_by_kind(list, wibbrlib.cmp.CMP_BLKID),
            "blkid")
        self.failUnlessEqual(len(list), 2)
        o2 = wibbrlib.cmp.first_by_kind(list, wibbrlib.cmp.CMP_OBJECT)
        self.failUnlessEqual(wibbrlib.obj.first_string_by_kind(o, 2), 
                             "pretty")
        self.failUnlessEqual(object_queue_ids(oq), ["pink"])


class InodeTests(unittest.TestCase):

    def testEncodeDecode(self):
        stats1 = normalize_stat_result(os.stat("Makefile"))
        id1 = "xyzzy"
        sigref1 = "maze"
        contref1 = "plugh"
        inode = inode_object_encode(id1, stats1, sigref1, contref1)
        (id2, stats2, sigref2, contref2) = inode_object_decode(inode)
        self.failUnlessEqual(id1, id2)
        self.failUnlessEqual(stats1, stats2)
        self.failUnlessEqual(sigref1, sigref2)
        self.failUnlessEqual(contref1, contref2)


class GenerationTests(unittest.TestCase):

    def testEncodeDecode(self):
        id1 = "xyzzy"
        pairs1 = [("inode1", "cont1"), ("inode2", "cont2")]
        gen = generation_object_encode(id1, pairs1)
        (id2, pairs2) = generation_object_decode(gen)
        self.failUnlessEqual(id1, id2)
        self.failUnlessEqual(pairs1, pairs2)


class NormalizedInodeTests(unittest.TestCase):

    def testNormalization(self):
        st1 = os.stat("Makefile")
        st2 = os.stat(".")
        st3 = os.stat("..")
        nst1 = normalize_stat_result(st1)
        nst2 = normalize_stat_result(st2)
        nst3 = normalize_stat_result(st3)
        self.failUnlessEqual(nst1, normalize_stat_result(st1))
        self.failUnlessEqual(nst2, normalize_stat_result(st2))
        self.failUnlessEqual(nst3, normalize_stat_result(st3))
        self.failIfEqual(nst1, nst2)
        self.failIfEqual(nst2, nst3)
        self.failIfEqual(nst3, nst1)


class ObjectTests(unittest.TestCase):

    def testId(self):
        id = wibbrlib.obj.object_id_new()
        self.failIfEqual(id, None)
        self.failUnlessEqual(type(id), type(""))

    def testCreateSignatureObject(self):
        id = "pink"
        sig = wibbrlib.rsync.compute_signature("Makefile")
        encoded = signature_object_encode(id, sig)
        o = wibbrlib.obj.decode(encoded, 0)
        self.failUnlessEqual(wibbrlib.obj.get_id(o), "pink")
        self.failUnlessEqual(wibbrlib.obj.get_kind(o), wibbrlib.obj.OBJ_SIG)
        self.failUnlessEqual(len(wibbrlib.obj.get_components(o)), 1)
        self.failUnlessEqual(
            wibbrlib.obj.first_string_by_kind(o, wibbrlib.cmp.CMP_SIGDATA),
            sig)


class HostBlockTests(unittest.TestCase):

    def testEncodeDecode(self):
        host_id = "pink"
        gen_ids = ["pretty", "beautiful"]
        map_ids = ["black", "box"]
        host = wibbrlib.obj.host_block_encode(host_id, gen_ids, map_ids)
        self.failUnless(host.startswith(wibbrlib.obj.BLOCK_COOKIE))
        (host_id2, gen_ids2, map_ids2) = wibbrlib.obj.host_block_decode(host)
        self.failUnlessEqual(host_id, host_id2)
        self.failUnlessEqual(gen_ids, gen_ids2)
        self.failUnlessEqual(map_ids, map_ids2)
        
    def testFormatVersion(self):
        encoded = wibbrlib.obj.host_block_encode("pink", [], [])
        decoded = wibbrlib.obj.block_decode(encoded)
        c = wibbrlib.cmp.first_by_kind(decoded, wibbrlib.cmp.CMP_OBJECT)
        subs = wibbrlib.cmp.get_subcomponents(c)
        id = wibbrlib.cmp.first_string_by_kind(subs, wibbrlib.cmp.CMP_OBJID)
        self.failUnlessEqual(id, "pink")
        ver = wibbrlib.cmp.first_string_by_kind(subs, 
                                            wibbrlib.cmp.CMP_FORMATVERSION)
        self.failUnlessEqual(ver, "1")


class GetComponentTests(unittest.TestCase):

    def setUp(self):
        self.o = wibbrlib.obj.create("uuid", 0)
        wibbrlib.obj.add(self.o, wibbrlib.cmp.create(1, "pink"))
        wibbrlib.obj.add(self.o, wibbrlib.cmp.create(2, "pretty"))
        wibbrlib.obj.add(self.o, wibbrlib.cmp.create(3, "red"))
        wibbrlib.obj.add(self.o, wibbrlib.cmp.create(3, "too"))

    def testGetByKind(self):
        find = lambda t: \
            [wibbrlib.cmp.get_string_value(c) 
                for c in wibbrlib.obj.find_by_kind(self.o, t)]
        self.failUnlessEqual(find(1), ["pink"])
        self.failUnlessEqual(find(2), ["pretty"])
        self.failUnlessEqual(find(3), ["red", "too"])
        self.failUnlessEqual(find(0), [])

    def testGetStringsByKind(self):
        find = lambda t: wibbrlib.obj.find_strings_by_kind(self.o, t)
        self.failUnlessEqual(find(1), ["pink"])
        self.failUnlessEqual(find(2), ["pretty"])
        self.failUnlessEqual(find(3), ["red", "too"])
        self.failUnlessEqual(find(0), [])

    def helper(self, wanted_kind):
        c = wibbrlib.obj.first_by_kind(self.o, wanted_kind)
        if c:
            return wibbrlib.cmp.get_string_value(c)
        else:
            return None

    def testGetFirstByKind(self):
        self.failUnlessEqual(self.helper(1), "pink")
        self.failUnlessEqual(self.helper(2), "pretty")
        self.failUnlessEqual(self.helper(3), "red")
        self.failUnlessEqual(self.helper(0), None)

    def testGetFirstStringByKind(self):
        find = lambda t: wibbrlib.obj.first_string_by_kind(self.o, t)
        self.failUnlessEqual(find(1), "pink")
        self.failUnlessEqual(find(2), "pretty")
        self.failUnlessEqual(find(3), "red")
        self.failUnlessEqual(find(0), None)

    def testGetVarintsByKind(self):
        list = range(1024)

        o = wibbrlib.obj.create("uuid", 0)
        for i in list:
            c = wibbrlib.cmp.create(0, wibbrlib.varint.encode(i))
            wibbrlib.obj.add(o, c)

        self.failUnlessEqual(wibbrlib.obj.find_varints_by_kind(o, 0), list)

    def testGetFirstSVarintByKind(self):
        o = wibbrlib.obj.create("uuid", 0)
        for i in range(1024):
            c = wibbrlib.cmp.create(i, wibbrlib.varint.encode(i))
            wibbrlib.obj.add(o, c)

        for i in range(1024):
            self.failUnlessEqual(wibbrlib.obj.first_varint_by_kind(o, i), i)
