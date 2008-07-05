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


"""Unit tests for obnamlib.rsync."""


import os
import shutil
import tempfile
import unittest


import obnamlib


class RsyncTests(unittest.TestCase):

    def setUp(self):
        self.tempfiles = []
        self.empty = self.create_temporary_file("")
        self.context = obnamlib.context.Context()
        self.context.cache = obnamlib.cache.Cache(self.context.config)
        self.context.be = obnamlib.backend.init(self.context.config, 
                                                self.context.cache)
        
    def tearDown(self):
        for filename in self.tempfiles:
            if os.path.exists(filename):
                os.remove(filename)

    def create_temporary_file(self, contents):
        (fd, filename) = tempfile.mkstemp()
        os.close(fd)
        obnamlib.create_file(filename, contents)
        self.tempfiles.append(filename)
        return filename

    def testSignature(self):
        empty_sig = self.create_temporary_file("")
        sig = obnamlib.rsync.compute_signature(self.context, self.empty)
        os.system("rdiff signature %s %s" % (self.empty, empty_sig))
        data = obnamlib.read_file(empty_sig)
        self.failUnlessEqual(sig, data)

    def testSignatureRaisesExceptionIfCommandIsUnknown(self):
        self.failUnlessRaises(obnamlib.rsync.UnknownCommand,
                              obnamlib.rsync.compute_signature,
                              self.context, self.empty, 
                              rdiff="unknown_command")

    def testSignatureRaisesExceptionIfCommandFails(self):
        self.failUnlessRaises(obnamlib.rsync.CommandFailure,
                              obnamlib.rsync.compute_signature,
                              self.context, self.empty, rdiff="false")

    def testDeltaRaisesExceptionIfCommandFails(self):
        self.failUnlessRaises(obnamlib.rsync.CommandFailure,
                              obnamlib.rsync.compute_delta,
                              self.context, "pink", self.empty)

    def testEmptyDelta(self):
        sig = obnamlib.rsync.compute_signature(self.context, self.empty)
        deltapart_ids = obnamlib.rsync.compute_delta(self.context, sig, 
                                                     self.empty)

        self.failUnlessEqual(len(deltapart_ids), 1)

        obnamlib.io.flush_all_object_queues(self.context)
        delta = obnamlib.io.get_object(self.context, deltapart_ids[0])
        self.failIfEqual(delta, None)
        delta = delta.first_string_by_kind(obnamlib.cmp.DELTADATA)

        # The hex string below is what rdiff outputs. I've no idea what
        # the format is, and the empty delta is expressed differently
        # in different situations. Eventually we'll move away from rdiff,
        # and then this should become clearer. --liw, 2006-09-24
        self.failUnlessEqual(delta, "rs\x026\x00")
        
        shutil.rmtree(self.context.config.get("backup", "store"))
        
    def testApplyDelta(self):
        first = self.create_temporary_file("pink")
        second = self.create_temporary_file("pretty")
        sig = obnamlib.rsync.compute_signature(self.context, first)
        deltapart_ids = obnamlib.rsync.compute_delta(self.context, sig, second)
        obnamlib.io.flush_all_object_queues(self.context)
        
        third = self.create_temporary_file("")
        obnamlib.rsync.apply_delta(self.context, first, deltapart_ids, third)
        
        third_data = obnamlib.read_file(third)

        self.failUnlessEqual(third_data, "pretty")
        
        shutil.rmtree(self.context.config.get("backup", "store"))

    def raise_os_error(self, *args):
        raise os.error("foo")

    def testApplyDeltaWithoutDevNull(self):
        self.failUnlessRaises(os.error,
                              obnamlib.rsync.apply_delta, 
                              None, None, None, None, 
                              open=self.raise_os_error)

    def testApplyDeltaRaisesExceptionWhenCommandFails(self):
        first = self.create_temporary_file("pink")
        second = self.create_temporary_file("pretty")
        sig = obnamlib.rsync.compute_signature(self.context, first)
        deltapart_ids = obnamlib.rsync.compute_delta(self.context, sig, second)
        obnamlib.io.flush_all_object_queues(self.context)

        self.failUnlessRaises(obnamlib.rsync.CommandFailure,
                              obnamlib.rsync.apply_delta,
                              self.context, first, deltapart_ids, "/dev/null",
                              cmd="./badcat")

        shutil.rmtree(self.context.config.get("backup", "store"))
