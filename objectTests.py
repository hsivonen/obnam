"""Unit tests for wibbrlib.object."""


import os
import unittest


from wibbrlib.object import *
import wibbrlib


class ObjectTypeNameTests(unittest.TestCase):

    def test(self):
        self.failUnlessEqual(object_type_name(-12765), "OBJ_UNKNOWN")
        self.failUnlessEqual(object_type_name(OBJ_FILEPART), "OBJ_FILEPART")
        self.failUnlessEqual(object_type_name(OBJ_INODE), "OBJ_INODE")
        self.failUnlessEqual(object_type_name(OBJ_GEN), "OBJ_GEN")
        self.failUnlessEqual(object_type_name(OBJ_SIG), "OBJ_SIG")
        self.failUnlessEqual(object_type_name(OBJ_HOST), "OBJ_HOST")


class ObjectCreateTests(unittest.TestCase):

    def testCreate(self):
        o = wibbrlib.object.create("pink", 1)
        self.failUnlessEqual(wibbrlib.object.get_id(o), "pink")
        self.failUnlessEqual(wibbrlib.object.get_type(o), 1)
        self.failUnlessEqual(wibbrlib.object.get_components(o), [])

    def testAdd(self):
        o = wibbrlib.object.create("pink", 1)
        c = wibbrlib.component.create(2, "pretty")
        wibbrlib.object.add(o, c)
        self.failUnlessEqual(wibbrlib.object.get_components(o), [c])


class ObjectEncodingTests(unittest.TestCase):

    def testEmptyObject(self):
        o = wibbrlib.object.create("pink", 33)
        self.failUnlessEqual(wibbrlib.object.encode(o), "\4\1pink\1\2\41")

    def testNonEmptyObject(self):
        o = wibbrlib.object.create("pink", 33)
        c = wibbrlib.component.create(1, "pretty")
        wibbrlib.object.add(o, c)
        self.failUnlessEqual(wibbrlib.object.encode(o),
                             "\4\1pink\1\2\41\6\1pretty")


class ObjectEncodingDecodingTests(unittest.TestCase):

    def test(self):
        c1 = wibbrlib.component.create(0xdeadbeef, "hello")
        c2 = wibbrlib.component.create(0xcafebabe, "world")
        o = wibbrlib.object.create("uuid", 0xdada)
        wibbrlib.object.add(o, c1)
        wibbrlib.object.add(o, c2)
        
        encoded = wibbrlib.object.encode(o)
        o2 = wibbrlib.object.decode(encoded, 0)
        encoded2 = wibbrlib.object.encode(o2)
        
        self.failUnlessEqual(encoded, encoded2)
        return
        
        self.failUnlessEqual(len(components), 4) # id, type, cmpnt1, cmpnt2
        
        self.failUnlessEqual(components[0], (wibbrlib.component.CMP_OBJID, "uuid"))
        self.failUnlessEqual(components[1], (wibbrlib.component.CMP_OBJTYPE, 0xdada))
        self.failUnlessEqual(components[2], (0xdeadbeef, "hello"))
        self.failUnlessEqual(components[3], (0xcafebabe, "world"))


class OldObjectEncodingTests(unittest.TestCase):

    def testEmptyObject(self):
        self.failUnlessEqual(object_encode("uuid", 33, []),
                             "\4\1uuid\1\2\41")

    def testNonEmptyObject(self):
        self.failUnlessEqual(object_encode("uuid", 33, ["\1\77x"]),
                             "\4\1uuid\1\2\41\1\77x")


class OldObjectEncodingDecodingTests(unittest.TestCase):

    def test(self):
        component1 = wibbrlib.component.component_encode(0xdeadbeef, "hello")
        component2 = wibbrlib.component.component_encode(0xcafebabe, "world")
        object = object_encode("uuid", 0xdada, [component1, component2])
        self.failIfEqual(object, None)
        self.failIfEqual(object, "")
        
        components = object_decode(object, 0)
        self.failUnlessEqual(len(components), 4) # id, type, cmpnt1, cmpnt2
        
        self.failUnlessEqual(components[0], (wibbrlib.component.CMP_OBJID, "uuid"))
        self.failUnlessEqual(components[1], (wibbrlib.component.CMP_OBJTYPE, 0xdada))
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


class BlockCreateTests(unittest.TestCase):

    def testEmptyObjectQueue(self):
        oq = object_queue_create()
        block = block_create_from_object_queue("blkid", oq)
        self.failUnlessEqual(block, "\5\3blkid")
        self.failUnlessEqual(object_queue_ids(oq), [])

    def testObjectQueue(self):
        oq = object_queue_create()
        object_queue_add(oq, "xx", "foo")
        block = block_create_from_object_queue("blkid", oq)
        self.failUnlessEqual(block, "\5\3blkid\3\5foo")
        self.failUnlessEqual(object_queue_ids(oq), ["xx"])


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
        id = wibbrlib.object.object_id_new()
        self.failIfEqual(id, None)
        self.failUnlessEqual(type(id), type(""))

    def testCreateSignatureObject(self):
        id = "pink"
        sig = wibbrlib.rsync.compute_signature("Makefile")
        object = signature_object_encode(id, sig)
        self.failUnlessEqual(object, "".join(["\4\1pink", # obj id
                                              "\1\2\4",   # obj type
                                              chr(len(sig)) + "\30" + sig,
                                              ]))


class HostBlockTests(unittest.TestCase):

    def testEncodeDecode(self):
        host_id = "pink"
        gen_ids = ["pretty", "beautiful"]
        map_ids = ["black", "box"]
        host = wibbrlib.object.host_block_encode(host_id, gen_ids, map_ids)
        (host_id2, gen_ids2, map_ids2) = \
            wibbrlib.object.host_block_decode(host)
        self.failUnlessEqual(host_id, host_id2)
        self.failUnlessEqual(gen_ids, gen_ids2)
        self.failUnlessEqual(map_ids, map_ids2)
