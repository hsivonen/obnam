# Copyright (C) 2009  Lars Wirzenius <liw@liw.fi>
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


import hashlib
import StringIO
import unittest
import zlib

import obnamlib


class ObsyncSignatureTests(unittest.TestCase):

    def setUp(self):
        self.obsync = obnamlib.Obsync()
        
    def test_weak_checksum_returns_the_right_checksum(self):
        data = "foo"
        checksum = self.obsync.weak_checksum(data)
        self.assertEqual(checksum.kind, obnamlib.ADLER32)
        self.assertEqual(str(checksum), str(zlib.adler32(data)))
        
    def test_strong_checksum_returns_the_right_checksum(self):
        data = "foo"
        checksum = self.obsync.strong_checksum(data)
        self.assertEqual(checksum.kind, obnamlib.MD5)
        self.assertEqual(str(checksum), hashlib.md5(data).digest())
        
    def test_block_signature_returns_the_right_checksums(self):
        sig = self.obsync.block_signature("foo")
        self.assertEqual(sig.kind, obnamlib.CHECKSUMS)
        self.assert_(sig.first(kind=obnamlib.ADLER32))
        self.assert_(sig.first(kind=obnamlib.MD5))
        
    def test_file_signature_returns_empty_list_for_empty_file(self):
        sigs = self.obsync.file_signature(StringIO.StringIO(""), 42)
        self.assertEqual(sigs, [])
        
    def test_file_signature_returns_right_number_of_sigs_for_file(self):
        data = "x" * 64
        block_size = 13
        num_blocks = len(data) / block_size
        if len(data) % block_size:
            num_blocks += 1
        sigs = self.obsync.file_signature(StringIO.StringIO(data), block_size)
        self.assertEqual(len(sigs), num_blocks)
        for sig in sigs:
            self.assert_(isinstance(sig, obnamlib.Checksums))

    def test_make_signature_returns_rsyncsig_object(self):
        data = "x" * 64
        block_size = 13
        num_blocks = len(data) / block_size
        if len(data) % block_size:
            num_blocks += 1
        o = self.obsync.make_signature("id", StringIO.StringIO(data), block_size)
        self.assert_(isinstance(o, obnamlib.RsyncSig))
        self.assertEqual(o.kind, obnamlib.RSYNCSIG)
        self.assertEqual(o.id, "id")
        self.assertEqual(o.block_size, block_size)
        self.assertEqual(len(o.checksums), num_blocks)


class ObsyncDeltaTests(unittest.TestCase):

    def setUp(self):
        self.obsync = obnamlib.Obsync()
        self.old_data = "x" * 64
        self.new_data = self.old_data + "y" * 64
        self.block_size = 7

    def test_file_delta_returns_empty_list_for_no_difference(self):
        oldf = StringIO.StringIO(self.old_data)
        sig = self.obsync.make_signature("id", oldf, self.block_size)
        newf = StringIO.StringIO(self.old_data)
        delta = self.obsync.file_delta(sig, newf)
        self.assertEqual(delta, [])

