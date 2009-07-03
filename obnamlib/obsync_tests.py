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


import StringIO
import unittest

import obnamlib


class ObsyncTests(unittest.TestCase):

    def setUp(self):
        self.obsync = obnamlib.Obsync()
        
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

