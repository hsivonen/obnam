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


class ChecksumTests(unittest.TestCase):
        
    def test_weak_checksum_returns_the_right_checksum(self):
        data = "foo"
        checksum = obnamlib.obsync.weak_checksum(data)
        self.assertEqual(checksum.kind, obnamlib.ADLER32)
        self.assertEqual(str(checksum), str(zlib.adler32(data)))
        
    def test_strong_checksum_returns_the_right_checksum(self):
        data = "foo"
        checksum = obnamlib.obsync.strong_checksum(data)
        self.assertEqual(checksum.kind, obnamlib.MD5)
        self.assertEqual(str(checksum), hashlib.md5(data).digest())


class RsyncSignatureGeneratorTests(unittest.TestCase):

    def setUp(self):
        self.siggen = obnamlib.RsyncSignatureGenerator()
        
    def test_block_signature_returns_the_right_checksums(self):
        sig = self.siggen.block_signature("foo")
        self.assertEqual(sig.kind, obnamlib.CHECKSUMS)
        self.assert_(sig.first(kind=obnamlib.ADLER32))
        self.assert_(sig.first(kind=obnamlib.MD5))

    def test_file_signature_returns_empty_list_for_empty_file(self):
        sigs = list(self.siggen.file_signature(StringIO.StringIO(""), 42))
        self.assertEqual(sigs, [])
        
    def test_file_signature_returns_right_number_of_sigs_for_file(self):
        data = "x" * 64
        block_size = 13
        num_blocks = len(data) / block_size
        if len(data) % block_size:
            num_blocks += 1
        f = StringIO.StringIO(data)
        sigs = list(self.siggen.file_signature(f, block_size))
        self.assertEqual(len(sigs), num_blocks)
        for sig in sigs:
            self.assert_(isinstance(sig, obnamlib.Checksums))


class RsyncLookupTableTests(unittest.TestCase):

    def setUp(self):
        siggen = obnamlib.RsyncSignatureGenerator()
        block_size = 10
        self.block1 = "x" * block_size
        self.block2 = "y" * block_size
        data = self.block1 + self.block2
        f = StringIO.StringIO(data)
        self.checksums = siggen.file_signature(f, block_size)
        self.table = obnamlib.RsyncLookupTable()
        self.table.add_checksums(self.checksums)

    def test_defaults_to_fast_getitem(self):
        table = obnamlib.RsyncLookupTable()
        self.assertEqual(table.wanted__getitem__, table.fast__getitem__)

    def test_switches_to_real_getitem_when_checksums_have_been_added(self):
        self.assertEqual(self.table.wanted__getitem__, 
                         self.table.real__getitem__)

    def test_fast_getitem_returns_None_always(self):
        self.assertEqual(self.table.fast__getitem__(self.block1), None)

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
        table = obnamlib.RsyncLookupTable(compute_weak=lambda s: '0', 
                                          compute_strong=lambda s: s)
        table.add_checksums(checksums)
        self.assertEqual(table[self.block1], 0)
        self.assertEqual(table[self.block2], 1)


class RsyncDeltaGeneratorTests(unittest.TestCase):

    def setUp(self):
        siggen = obnamlib.RsyncSignatureGenerator()
        self.old_data = "".join(chr(i) for i in range(64))
        self.additional_data = "".join(chr(i) 
                for i in range(len(self.old_data), len(self.old_data) + 128))
        self.new_data = self.old_data + self.additional_data
        self.block_size = 7
        self.chunk_size = 1024**2
        oldf = StringIO.StringIO(self.old_data)
        checksums = list(siggen.file_signature(oldf, self.block_size))
        self.sigparts = [obnamlib.RsyncSigPart(id="id", 
                                               block_size=self.block_size, 
                                               checksums=checksums)]
        self.table = obnamlib.RsyncLookupTable()
        for x in self.sigparts:
            self.table.add_checksums(x.checksums)
        self.old_file = StringIO.StringIO(self.old_data)
        self.new_file = StringIO.StringIO(self.new_data)
        self.deltagen = obnamlib.RsyncDeltaGenerator(self.block_size,
                                                     self.table,
                                                     self.chunk_size)

    def test_returns_single_tuple_for_no_difference(self):
        deltagen = obnamlib.RsyncDeltaGenerator(self.block_size,
                                                self.table, 
                                                self.chunk_size)
        delta = list(deltagen.feed(self.old_file.read()))
        delta += list(deltagen.feed(""))
        self.assertEqual(len(delta), 1)
        c = delta[0]
        self.assertEqual(type(c), tuple)
        self.assertEqual(c[0], 0)
        self.assertEqual(c[1], len(self.old_data))

    def test_file_delta_computes_delta_correctly_for_changes(self):
        delta = list(self.deltagen.feed(self.new_file.read()))
        delta += list(self.deltagen.feed(""))

        self.assertEqual(len(delta), 2)

        self.assertEqual(type(delta[0]), tuple)
        self.assertEqual(delta[0][0], 0)
        # The algorithm only finds full blocks: new_data has junk after
        # the last partial block at the end of old_data, which is why
        # it isn't found.
        full_blocks = len(self.old_data) / self.block_size
        self.assertEqual(delta[0][1], full_blocks * self.block_size)

        self.assertEqual(type(delta[1]), str)
        old_tail = self.old_data[full_blocks * self.block_size : ]
        self.assertEqual(delta[1], old_tail + self.additional_data)

    def test_file_delta_computes_delta_for_leading_changes(self):
        data = self.additional_data + self.old_data
        f = StringIO.StringIO(data)
        deltagen = obnamlib.RsyncDeltaGenerator(self.block_size,
                                                self.table,
                                                self.chunk_size)
        delta = list(deltagen.feed(f.read()))
        delta += list(deltagen.feed(""))

        self.assertEqual(len(delta), 2, delta)

        self.assertEqual(type(delta[0]), str)
        self.assertEqual(delta[0], self.additional_data)

        self.assertEqual(type(delta[1]), tuple)
        self.assertEqual(delta[1][0], 0)
        self.assertEqual(delta[1][1], len(self.old_data))
        
    def test_file_delta_computes_delta_for_duplicated_block(self):
        data = self.old_data[:self.block_size] + self.old_data
        f = StringIO.StringIO(data)
        deltagen = obnamlib.RsyncDeltaGenerator(self.block_size,
                                                self.table,
                                                self.chunk_size)
        delta = list(deltagen.feed(f.read()))
        delta += list(deltagen.feed(""))

        self.assertEqual(len(delta), 2, delta)

        self.assertEqual(type(delta[0]), tuple)
        self.assertEqual(delta[0][0], 0)
        self.assertEqual(delta[0][1], self.block_size)

        self.assertEqual(type(delta[1]), tuple)
        self.assertEqual(delta[1][0], 0)
        self.assertEqual(delta[1][1], len(self.old_data))

