"""Unit tests for obnam.obj."""


import os
import unittest


from obnam.obj import *
import obnam


class ObjectKindNameTests(unittest.TestCase):

    def test(self):
        self.failUnlessEqual(kind_name(-12765), "OBJ_UNKNOWN")
        self.failUnlessEqual(kind_name(OBJ_FILEPART), "OBJ_FILEPART")
        self.failUnlessEqual(kind_name(OBJ_INODE), "OBJ_INODE")
        self.failUnlessEqual(kind_name(OBJ_GEN), "OBJ_GEN")
        self.failUnlessEqual(kind_name(OBJ_SIG), "OBJ_SIG")
        self.failUnlessEqual(kind_name(OBJ_HOST), "OBJ_HOST")
        self.failUnlessEqual(kind_name(OBJ_FILECONTENTS), "OBJ_FILECONTENTS")
        self.failUnlessEqual(kind_name(OBJ_FILELIST), "OBJ_FILELIST")


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
                             (obnam.cmp.CMP_OBJID, "uuid"))
        self.failUnlessEqual(components[1], 
                             (obnam.cmp.CMP_OBJKIND, 0xdada))
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
        self.failUnless(object_queue_is_empty(oq))
        object_queue_add(oq, "xx", "abc")
        self.failUnlessEqual(object_queue_combined_size(oq), 3)
        object_queue_add(oq, "yy", "abc")
        self.failUnlessEqual(object_queue_combined_size(oq), 6)

    def testClear(self):
        oq = object_queue_create()
        oq_orig = oq
        self.failUnless(object_queue_is_empty(oq))
        object_queue_clear(oq)
        self.failUnlessEqual(object_queue_combined_size(oq), 0)
        object_queue_add(oq, "xx", "abc")
        self.failUnlessEqual(object_queue_combined_size(oq), 3)
        object_queue_clear(oq)
        self.failUnless(object_queue_is_empty(oq))
        self.failUnless(oq == oq_orig)


class BlockCreateTests(unittest.TestCase):

    def testEmptyObjectQueue(self):
        oq = object_queue_create()
        block = block_create_from_object_queue("blkid", oq)
        list = obnam.obj.block_decode(block)
        self.failUnlessEqual(
            obnam.cmp.first_string_by_kind(list, obnam.cmp.CMP_BLKID),
            "blkid")
        self.failUnlessEqual(len(list), 1)
        self.failUnlessEqual(object_queue_ids(oq), [])

    def testObjectQueue(self):
        o = obnam.obj.create("pink", 1)
        obnam.obj.add(o, obnam.cmp.create(2, "pretty"))
        oq = object_queue_create()
        object_queue_add(oq, "pink", obnam.obj.encode(o))
        block = block_create_from_object_queue("blkid", oq)

        list = obnam.obj.block_decode(block)
        self.failUnlessEqual(
            obnam.cmp.first_string_by_kind(list, obnam.cmp.CMP_BLKID),
            "blkid")
        self.failUnlessEqual(len(list), 2)
        o2 = obnam.cmp.first_by_kind(list, obnam.cmp.CMP_OBJECT)
        self.failUnlessEqual(obnam.obj.first_string_by_kind(o, 2), 
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
        id1 = "pink"
        fl1 = "pretty"
        gen = generation_object_encode(id1, fl1)
        (id2, fl2) = generation_object_decode(gen)
        self.failUnlessEqual(id1, id2)
        self.failUnlessEqual(fl1, fl2)


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
        id = obnam.obj.object_id_new()
        self.failIfEqual(id, None)
        self.failUnlessEqual(type(id), type(""))

    def testCreateSignatureObject(self):
        id = "pink"
        sig = obnam.rsync.compute_signature("Makefile")
        encoded = signature_object_encode(id, sig)
        o = obnam.obj.decode(encoded, 0)
        self.failUnlessEqual(obnam.obj.get_id(o), "pink")
        self.failUnlessEqual(obnam.obj.get_kind(o), obnam.obj.OBJ_SIG)
        self.failUnlessEqual(len(obnam.obj.get_components(o)), 1)
        self.failUnlessEqual(
            obnam.obj.first_string_by_kind(o, obnam.cmp.CMP_SIGDATA),
            sig)


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
        c = obnam.cmp.first_by_kind(decoded, obnam.cmp.CMP_OBJECT)
        subs = obnam.cmp.get_subcomponents(c)
        id = obnam.cmp.first_string_by_kind(subs, obnam.cmp.CMP_OBJID)
        self.failUnlessEqual(id, "pink")
        ver = obnam.cmp.first_string_by_kind(subs, 
                                            obnam.cmp.CMP_FORMATVERSION)
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
