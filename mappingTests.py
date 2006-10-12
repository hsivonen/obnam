"""Unit tests for wibbrlib.mapping."""


import unittest


import wibbrlib


class ObjectMappingTests(unittest.TestCase):

    def testEmpty(self):
        m = wibbrlib.mapping.create()
        self.failUnlessEqual(wibbrlib.mapping.count(m), 0)

    def testGetNonexisting(self):
        m = wibbrlib.mapping.create()
        blkids = wibbrlib.mapping.get(m, "pink")
        self.failUnlessEqual(blkids, None)

    def testAddOneMapping(self):
        m = wibbrlib.mapping.create()
        wibbrlib.mapping.add(m, "pink", "pretty")
        self.failUnlessEqual(wibbrlib.mapping.count(m), 1)
        
        blkids = wibbrlib.mapping.get(m, "pink")
        self.failUnlessEqual(blkids, ["pretty"])

    def testAddTwoMappings(self):
        m = wibbrlib.mapping.create()
        wibbrlib.mapping.add(m, "pink", "pretty")
        wibbrlib.mapping.add(m, "pink", "beautiful")
        self.failUnlessEqual(wibbrlib.mapping.count(m), 1)
        
        blkids = wibbrlib.mapping.get(m, "pink")
        self.failUnlessEqual(blkids, ["pretty", "beautiful"])

    def testGetNewMappings(self):
        m = wibbrlib.mapping.create()
        self.failUnlessEqual(wibbrlib.mapping.get_new(m), [])
        wibbrlib.mapping.add(m, "pink", "pretty")
        self.failUnlessEqual(wibbrlib.mapping.get_new(m), ["pink"])
        wibbrlib.mapping.reset_new(m)
        self.failUnlessEqual(wibbrlib.mapping.get_new(m), [])
        wibbrlib.mapping.add(m, "black", "beautiful")
        self.failUnlessEqual(wibbrlib.mapping.get_new(m), ["black"])

    def testMappingEncodings(self):
        # Set up a mapping
        m = wibbrlib.mapping.create()
        
        # It's empty; make sure encoding new ones returns an empty list
        list = wibbrlib.mapping.encode_new(m)
        self.failUnlessEqual(list, [])

        # Add a mapping
        wibbrlib.mapping.add(m, "pink", "pretty")

        # Encode the new mapping, make sure that goes well
        list = wibbrlib.mapping.encode_new(m)
        self.failUnlessEqual(len(list), 1)
        
        # Make sure the encoding is correct
        list2 = wibbrlib.component.component_decode_all(list[0], 0)
        self.failUnlessEqual(len(list2), 1)
        self.failUnlessEqual(list2[0][0], wibbrlib.component.CMP_OBJMAP)
        
        list3 = wibbrlib.component.component_decode_all(list2[0][1], 0)
        self.failUnlessEqual(len(list3), 2)
        self.failUnlessEqual(list3[0], 
                             (wibbrlib.component.CMP_OBJREF, "pink"))
        self.failUnlessEqual(list3[1], 
                             (wibbrlib.component.CMP_BLOCKREF, "pretty"))

        # Now try decoding with the official function
        block = wibbrlib.mapping.encode_new_to_block(m, "black")
        m2 = wibbrlib.mapping.create()
        wibbrlib.mapping.decode_block(m2, block)
        self.failUnlessEqual(wibbrlib.mapping.count(m2), 1)
        self.failUnlessEqual(wibbrlib.mapping.get(m2, "pink"), ["pretty"])
