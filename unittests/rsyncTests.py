"""Unit tests for obnam.rsync."""


import os
import tempfile
import unittest


import obnam


class RsyncTests(unittest.TestCase):

    def testPipeline(self):
        p = obnam.rsync.pipeline(["/bin/echo", "foo"], ["cat"])
        output = p.stdout.read()
        exit = p.wait()
        self.failUnlessEqual(output, "foo\n")
        self.failUnlessEqual(exit, 0)

    def testSignature(self):
        sig = obnam.rsync.compute_signature("/dev/null")
        os.system("rdiff signature /dev/null devnull.sig.temp")
        f = file("devnull.sig.temp")
        data = f.read()
        f.close()
        self.failUnlessEqual(sig, data)
        os.remove("devnull.sig.temp")

    def testEmptyDelta(self):
        sig = obnam.rsync.compute_signature("/dev/null")
        delta = obnam.rsync.compute_delta(sig, "/dev/null")
        # The hex string below is what rdiff outputs. I've no idea what
        # the format is, and the empty delta is expressed differently
        # in different situations. Eventually we'll move away from rdiff,
        # and then this should become clearer. --liw, 2006-09-24
        self.failUnlessEqual(delta, "rs\x026\x00")

    def create_file(self, contents):
        (fd, filename) = tempfile.mkstemp()
        os.write(fd, contents)
        os.close(fd)
        return filename

    def testApplyDelta(self):
        first = self.create_file("pink")
        second = self.create_file("pretty")
        sig = obnam.rsync.compute_signature(first)
        delta = obnam.rsync.compute_delta(sig, second)

        (fd, third) = tempfile.mkstemp()
        os.close(fd)
        obnam.rsync.apply_delta(first, delta, third)
        
        f = file(third, "r")
        third_data = f.read()
        f.close()

        self.failUnlessEqual(third_data, "pretty")
