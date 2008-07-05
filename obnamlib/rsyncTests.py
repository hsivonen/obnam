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
        empty_file = self.create_temporary_file("")

        context = obnamlib.context.Context()
        sig = obnamlib.rsync.compute_signature(context, empty_file)
        os.system("rdiff signature %s empty_file.sig.temp" % empty_file)
        data = obnamlib.read_file("empty_file.sig.temp")
        self.failUnlessEqual(sig, data)
        os.remove("empty_file.sig.temp")

    def testSignatureRaisesExceptionIfCommandIsUnknown(self):
        empty_file = self.create_temporary_file("")
        context = obnamlib.context.Context()
        self.failUnlessRaises(obnamlib.rsync.UnknownCommand,
                              obnamlib.rsync.compute_signature,
                              context, empty_file, rdiff="unknown_command")

    def testSignatureRaisesExceptionIfCommandFails(self):
        empty_file = self.create_temporary_file("")
        context = obnamlib.context.Context()
        self.failUnlessRaises(obnamlib.rsync.CommandFailure,
                              obnamlib.rsync.compute_signature,
                              context, empty_file, rdiff="false")

    def testDeltaRaisesExceptionIfCommandFails(self):
        empty_file = self.create_temporary_file("")
        context = obnamlib.context.Context()
        self.failUnlessRaises(obnamlib.rsync.CommandFailure,
                              obnamlib.rsync.compute_delta,
                              context, "pink", empty_file)

    def testEmptyDelta(self):
        empty_file = self.create_temporary_file("")

        context = obnamlib.context.Context()
        context.cache = obnamlib.cache.Cache(context.config)
        context.be = obnamlib.backend.init(context.config, context.cache)

        sig = obnamlib.rsync.compute_signature(context, empty_file)
        deltapart_ids = obnamlib.rsync.compute_delta(context, sig, empty_file)

        self.failUnlessEqual(len(deltapart_ids), 1)

        obnamlib.io.flush_all_object_queues(context)
        delta = obnamlib.io.get_object(context, deltapart_ids[0])
        self.failIfEqual(delta, None)
        delta = delta.first_string_by_kind(obnamlib.cmp.DELTADATA)

        # The hex string below is what rdiff outputs. I've no idea what
        # the format is, and the empty delta is expressed differently
        # in different situations. Eventually we'll move away from rdiff,
        # and then this should become clearer. --liw, 2006-09-24
        self.failUnlessEqual(delta, "rs\x026\x00")
        
        shutil.rmtree(context.config.get("backup", "store"))
        
    def testApplyDelta(self):
        context = obnamlib.context.Context()
        context.cache = obnamlib.cache.Cache(context.config)
        context.be = obnamlib.backend.init(context.config, context.cache)
        
        first = self.create_temporary_file("pink")
        second = self.create_temporary_file("pretty")
        sig = obnamlib.rsync.compute_signature(context, first)
        deltapart_ids = obnamlib.rsync.compute_delta(context, sig, second)
        obnamlib.io.flush_all_object_queues(context)
        
        third = self.create_temporary_file("")
        obnamlib.rsync.apply_delta(context, first, deltapart_ids, third)
        
        third_data = obnamlib.read_file(third)

        self.failUnlessEqual(third_data, "pretty")
        
        shutil.rmtree(context.config.get("backup", "store"))

    def raise_os_error(self, *args):
        raise os.error("foo")

    def testApplyDeltaWithoutDevNull(self):
        self.failUnlessRaises(os.error,
                              obnamlib.rsync.apply_delta, 
                              None, None, None, None, 
                              open=self.raise_os_error)

    def testApplyDeltaRaisesExceptionWhenCommandFails(self):
        context = obnamlib.context.Context()
        context.cache = obnamlib.cache.Cache(context.config)
        context.be = obnamlib.backend.init(context.config, context.cache)
        
        first = self.create_temporary_file("pink")
        second = self.create_temporary_file("pretty")
        sig = obnamlib.rsync.compute_signature(context, first)
        deltapart_ids = obnamlib.rsync.compute_delta(context, sig, second)
        obnamlib.io.flush_all_object_queues(context)

        self.failUnlessRaises(obnamlib.rsync.CommandFailure,
                              obnamlib.rsync.apply_delta,
                              context, first, deltapart_ids, "/dev/null",
                              cmd="./badcat")

        shutil.rmtree(context.config.get("backup", "store"))
