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
        (fd, empty_file) = tempfile.mkstemp()
        os.close(fd)

        context = obnam.context.create()
        sig = obnam.rsync.compute_signature(context, empty_file)
        os.system("rdiff signature %s empty_file.sig.temp" % empty_file)
        f = file("empty_file.sig.temp")
        data = f.read()
        f.close()
        self.failUnlessEqual(sig, data)
        os.remove("empty_file.sig.temp")
        os.remove(empty_file)

    def testEmptyDelta(self):
        (fd, empty_file) = tempfile.mkstemp()
        os.close(fd)
    
        context = obnam.context.create()
        sig = obnam.rsync.compute_signature(context, empty_file)
        delta = obnam.rsync.compute_delta(context, sig, empty_file)

        os.remove(empty_file)

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
        context = obnam.context.create()
        
        first = self.create_file("pink")
        second = self.create_file("pretty")
        sig = obnam.rsync.compute_signature(context, first)
        delta = obnam.rsync.compute_delta(context, sig, second)

        (fd, third) = tempfile.mkstemp()
        os.close(fd)
        obnam.rsync.apply_delta(first, delta, third)
        
        f = file(third, "r")
        third_data = f.read()
        f.close()

        self.failUnlessEqual(third_data, "pretty")
