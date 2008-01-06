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


"""Unit tests for obnam.rsync."""


import os
import shutil
import tempfile
import unittest


import obnam


class RsyncTests(unittest.TestCase):

    def testSignature(self):
        (fd, empty_file) = tempfile.mkstemp()
        os.close(fd)

        context = obnam.context.Context()
        sig = obnam.rsync.compute_signature(context, empty_file)
        os.system("rdiff signature %s empty_file.sig.temp" % empty_file)
        f = file("empty_file.sig.temp")
        data = f.read()
        f.close()
        self.failUnlessEqual(sig, data)
        os.remove("empty_file.sig.temp")
        os.remove(empty_file)

    def testSignatureRaisesExceptionIfCommandIsUnknown(self):
        (fd, empty_file) = tempfile.mkstemp()
        os.close(fd)

        context = obnam.context.Context()
        context.config.set("backup", "odirect-pipe", "/notexist")
        self.failUnlessRaises(obnam.rsync.UnknownCommand,
                              obnam.rsync.compute_signature,
                              context, empty_file)

        os.remove(empty_file)

    def testSignatureRaisesExceptionIfCommandFails(self):
        (fd, empty_file) = tempfile.mkstemp()
        os.close(fd)

        context = obnam.context.Context()
        context.config.set("backup", "odirect-pipe", "false")
        self.failUnlessRaises(obnam.rsync.CommandFailure,
                              obnam.rsync.compute_signature,
                              context, empty_file)

        os.remove(empty_file)

    def testDeltaRaisesExceptionIfCommandFails(self):
        (fd, empty_file) = tempfile.mkstemp()
        os.close(fd)

        context = obnam.context.Context()
        context.config.set("backup", "odirect-pipe", "false")
        self.failUnlessRaises(obnam.rsync.CommandFailure,
                              obnam.rsync.compute_delta,
                              context, "pink", empty_file)

        os.remove(empty_file)

    def testEmptyDelta(self):
        (fd, empty_file) = tempfile.mkstemp()
        os.close(fd)
    
        context = obnam.context.Context()
        context.cache = obnam.cache.Cache(context.config)
        context.be = obnam.backend.init(context.config, context.cache)

        sig = obnam.rsync.compute_signature(context, empty_file)
        deltapart_ids = obnam.rsync.compute_delta(context, sig, empty_file)

        os.remove(empty_file)
        self.failUnlessEqual(len(deltapart_ids), 1)

        obnam.io.flush_all_object_queues(context)
        delta = obnam.io.get_object(context, deltapart_ids[0])
        self.failIfEqual(delta, None)
        delta = delta.first_string_by_kind(obnam.cmp.DELTADATA)

        # The hex string below is what rdiff outputs. I've no idea what
        # the format is, and the empty delta is expressed differently
        # in different situations. Eventually we'll move away from rdiff,
        # and then this should become clearer. --liw, 2006-09-24
        self.failUnlessEqual(delta, "rs\x026\x00")
        
        shutil.rmtree(context.config.get("backup", "store"))
        
    def create_file(self, contents):
        (fd, filename) = tempfile.mkstemp()
        os.write(fd, contents)
        os.close(fd)
        return filename

    def testApplyDelta(self):
        context = obnam.context.Context()
        context.cache = obnam.cache.Cache(context.config)
        context.be = obnam.backend.init(context.config, context.cache)
        
        first = self.create_file("pink")
        second = self.create_file("pretty")
        sig = obnam.rsync.compute_signature(context, first)
        deltapart_ids = obnam.rsync.compute_delta(context, sig, second)
        obnam.io.flush_all_object_queues(context)

        (fd, third) = tempfile.mkstemp()
        os.close(fd)
        obnam.rsync.apply_delta(context, first, deltapart_ids, third)
        
        f = file(third, "r")
        third_data = f.read()
        f.close()

        self.failUnlessEqual(third_data, "pretty")
        
        shutil.rmtree(context.config.get("backup", "store"))
