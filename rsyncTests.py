"""Unit tests for wibbrlib.rsync."""


import os
import unittest


import wibbrlib


class RsyncTests(unittest.TestCase):

    def testSignature(self):
        sig = wibbrlib.rsync.compute_signature("/dev/null")
        os.system("rdiff signature /dev/null devnull.sig.temp")
        f = file("devnull.sig.temp")
        data = f.read()
        f.close()
        self.failUnlessEqual(sig, data)
        os.remove("devnull.sig.temp")

    def testEmptyDelta(self):
        sig = wibbrlib.rsync.compute_signature("/dev/null")
        delta = wibbrlib.rsync.compute_delta(sig, "/dev/null")
        # The hex string below is what rdiff outputs. I've no idea what
        # the format is, and the empty delta is expressed differently
        # in different situations. Eventually we'll move away from rdiff,
        # and then this should become clearer. --liw, 2006-09-24
        self.failUnlessEqual(delta, "rs\x026\x00")
