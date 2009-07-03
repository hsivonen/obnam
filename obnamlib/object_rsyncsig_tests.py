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


import os
import unittest

import obnamlib


class RsyncSigTests(unittest.TestCase):

    def setUp(self):
        self.checksums = [obnamlib.Checksums([])]
        self.o = obnamlib.RsyncSig(id="id", block_size=42, 
                                   checksums=self.checksums)

    def test_sets_id_correctly(self):
        self.assertEqual(self.o.id, "id")

    def test_sets_block_size_correctly(self):
        self.assertEqual(self.o.block_size, 42)

    def test_sets_checksums_correctly(self):
        self.assertEqual(self.o.checksums, self.checksums)

