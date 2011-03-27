# Copyright 2011  Lars Wirzenius
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


import unittest

import obnamlib


class SymmetricEncryptionTests(unittest.TestCase):

    # We don't test the quality of keys or encryption here. Doing that is
    # hard to do well, and we'll just assume that reading /dev/random
    # for keys, and using gpg for encryption, is going to work well.
    # In these tests, we care about making sure we use the tools right,
    # not that the tools themselves work right.

    def test_generates_key_of_correct_length(self):
        numbits = 16
        key = obnamlib.generate_symmetric_key(numbits)
        self.assertEqual(len(key) * 8, numbits)

    def test_generates_key_with_size_rounded_up(self):
        numbits = 15
        key = obnamlib.generate_symmetric_key(numbits)
        self.assertEqual(len(key), 2)

    def test_encrypts_into_different_string_than_cleartext(self):
        cleartext = 'hello world'
        key = 'sekr1t'
        encrypted = obnamlib.encrypt_with_symmetric_key(cleartext, key)
        self.assertNotEqual(cleartext, encrypted)

