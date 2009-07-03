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


class RsyncLookupTableTests(unittest.TestCase):

    def setUp(self):
        obsync = obnamlib.Obsync()
        block_size = 10
        self.block1 = "x" * block_size
        self.block2 = "y" * block_size
        data = self.block1 + self.block2
        f = StringIO.StringIO(data)
        self.checksums = obsync.file_signature(f, block_size)
        self.table = obnamlib.obsync.RsyncLookupTable(obsync.weak_checksum,
                                                      obsync.strong_checksum,
                                                      self.checksums)

    def test_finds_first_block(self):
        self.assertEqual(self.table[self.block1], 0)

    def test_finds_second_block(self):
        self.assertEqual(self.table[self.block2], 1)

    def test_does_not_find_new_block(self):
        self.assertEqual(self.table["z"], None)

    def test_handles_weak_collision(self):  
        checksums = [obnamlib.Checksums([obnamlib.Adler32('0'),
                                         obnamlib.Md5(self.block1)]),
                     obnamlib.Checksums([obnamlib.Adler32('0'),
                                         obnamlib.Md5(self.block2)])]
        table = obnamlib.obsync.RsyncLookupTable(lambda s: '0', lambda s: s,
                                                 checksums)
        self.assertEqual(table[self.block1], 0)
        self.assertEqual(table[self.block2], 1)


class ObsyncDeltaTests(unittest.TestCase):

    def setUp(self):
        self.obsync = obnamlib.Obsync()
        self.old_data = "".join(chr(i) for i in range(64))
        self.additional_data = "".join(chr(i) 
                for i in range(len(self.old_data), len(self.old_data) + 128))
        self.new_data = self.old_data + self.additional_data
        self.block_size = 7
        self.chunk_size = 1024**2
        oldf = StringIO.StringIO(self.old_data)
        self.sig = self.obsync.make_signature("id", oldf, self.block_size)
        self.old_file = StringIO.StringIO(self.old_data)
        self.new_file = StringIO.StringIO(self.new_data)

    def test_file_delta_returns_single_oldfilesubstr_for_no_difference(self):
        delta = self.obsync.file_delta(self.sig, self.old_file, 
                                       self.chunk_size)
        self.assertEqual(len(delta), 1)
        c = delta[0]
        self.assertEqual(c.kind, obnamlib.OLDFILESUBSTRING)
        self.assertEqual(c.offset, 0)
        self.assertEqual(c.length, len(self.old_data))

    def test_file_delta_computes_delta_correctly_for_changes(self):
        delta = self.obsync.file_delta(self.sig, self.new_file, 
                                       self.chunk_size)

        self.assertEqual(len(delta), 2)

        self.assertEqual(delta[0].kind, obnamlib.OLDFILESUBSTRING)
        self.assertEqual(delta[0].offset, 0)
        # The algorithm only finds full blocks: new_data has junk after
        # the last partial block at the end of old_data, which is why
        # it isn't found.
        full_blocks = len(self.old_data) / self.block_size
        self.assertEqual(delta[0].length, full_blocks * self.block_size)

        self.assertEqual(delta[1].kind, obnamlib.FILECHUNK)
        old_tail = self.old_data[full_blocks * self.block_size : ]
        self.assertEqual(str(delta[1]), old_tail + self.additional_data)

