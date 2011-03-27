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


import os
import shutil
import subprocess
import tempfile
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
        key = obnamlib.generate_symmetric_key(numbits, filename='/dev/zero')
        self.assertEqual(len(key) * 8, numbits)

    def test_generates_key_with_size_rounded_up(self):
        numbits = 15
        key = obnamlib.generate_symmetric_key(numbits, filename='/dev/zero')
        self.assertEqual(len(key), 2)

    def test_encrypts_into_different_string_than_cleartext(self):
        cleartext = 'hello world'
        key = 'sekr1t'
        encrypted = obnamlib.encrypt_with_symmetric_key(cleartext, key)
        self.assertNotEqual(cleartext, encrypted)

    def test_encrypt_decrypt_round_trip(self):
        cleartext = 'hello, world'
        key = 'sekr1t'
        encrypted = obnamlib.encrypt_with_symmetric_key(cleartext, key)
        decrypted = obnamlib.decrypt_with_symmetric_key(encrypted, key)
        self.assertEqual(decrypted, cleartext)


class GetPublicKeyTests(unittest.TestCase):

    def setUp(self):
        self.dirname = tempfile.mkdtemp()
        self.gpghome = os.path.join(self.dirname, 'gpghome')
        shutil.copytree('test-gpghome', self.gpghome)
        self.keyid = '1B321347'
        
    def tearDown(self):
        shutil.rmtree(self.dirname)
        
    def test_exports_key(self):
        key = obnamlib.get_public_key(self.keyid, gpghome=self.gpghome)
        self.assert_('-----BEGIN PGP PUBLIC KEY BLOCK-----' in key)


class KeyringTests(unittest.TestCase):

    def setUp(self):
        self.keyring = obnamlib.Keyring()
        self.keyid = '3B1802F81B321347'
        self.key = '''
-----BEGIN PGP PUBLIC KEY BLOCK-----
Version: GnuPG v1.4.10 (GNU/Linux)

mI0ETY8gwwEEAMrSXBIJseIv9miuwnYlCd7CQCzNb8nHYkpo4o1nEQD3k/h7xj9m
/0Gd5kLfF+WLwAxSJYb41JjaKs0FeUexSGNePdNFxn2CCZ4moHH19tTlWGfqCNz7
vcYQpSbPix+zhR7uNqilxtsIrx1iyYwh7L2VKf/KMJ7yXbT+jbAj7fqBABEBAAG0
CFRlc3QgS2V5iLgEEwECACIFAk2PIMMCGwMGCwkIBwMCBhUIAgkKCwQWAgMBAh4B
AheAAAoJEDsYAvgbMhNHlEED/1UkiLJ8R3phMRnjLtn+5JobYvOi7WEubnRv1rnN
MC4MyhFiLux7Z8p3xwt1Pf2GqL7q1dD91NOx+6KS3d1PFmiM/i1fYalZPbzm1gNr
8sFK2Gxsnd7mmYf2wKIo335Bk21SCmGcNKvmKW2M6ckzPT0q/RZ2hhY9JhHUiLG4
Lu3muI0ETY8gwwEEAMQoiBCQYky52pDamnH5c7FngCM72AkNq/z0+DHqY202gksd
Vy63TF7UGIsiCLvY787vPm62sOqYO0uI6PV5xVDGyJh4oI/g2zgNkhXRZrIB1Q+T
THp7qSmwQUZv8T+HfgxLiaXDq6oV/HWLElcMQ9ClZ3Sxzlu3ZQHrtmY5XridABEB
AAGInwQYAQIACQUCTY8gwwIbDAAKCRA7GAL4GzITR4hgBAClEurTj5n0/21pWZH0
Ljmokwa3FM++OZxO7shc1LIVNiAKfLiPigU+XbvSeVWTeajKkvj5LCVxKQiRSiYB
Z85TYTo06kHvDCYQmFOSGrLsZxMyJCfHML5spF9+bej5cepmuNVIdJK5vlgDiVr3
uWUO7gMi+AlnxbfXVCTEgw3xhg==
=j+6W
-----END PGP PUBLIC KEY BLOCK-----
'''

    def test_has_no_keys_initially(self):
        self.assertEqual(self.keyring.keyids(), [])
        self.assertEqual(str(self.keyring), '')

    def test_gets_no_keys_from_empty_encoded(self):
        keyring = obnamlib.Keyring(encoded='')
        self.assertEqual(keyring.keyids(), [])
        
    def test_adds_key(self):
        self.keyring.add(self.key)
        self.assertEqual(self.keyring.keyids(), [self.keyid])
        self.assert_(self.keyid in self.keyring)
        
    def test_removes_key(self):
        self.keyring.add(self.key)
        self.keyring.remove(self.keyid)
        self.assertEqual(self.keyring.keyids(), [])
        
    def test_export_import_roundtrip_works(self):
        self.keyring.add(self.key)
        exported = str(self.keyring)
        keyring2 = obnamlib.Keyring(exported)
        self.assertEqual(keyring2.keyids(), [self.keyid])

