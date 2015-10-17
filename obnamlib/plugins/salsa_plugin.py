# Copyright (C) 2011-2015  Lars Wirzenius
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


import base64
import curses
import logging
import os
import pysodium
import sys

import obnamlib


class WrongNumberOfScryptComponentsError(obnamlib.ObnamError):

    msg = 'Wrong number of colon-separated components in scrypt specifier'

class EmptyScryptWorkMultiplierError(obnamlib.ObnamError):

    msg = 'Empty scrypt work multiplier'

class EmptyScryptMemoryError(obnamlib.ObnamError):

    msg = 'Empty scrypt memory amount'

class NonIntScryptOperationSpecifierError(obnamlib.ObnamError):

    msg = 'Scrypt work factor is not a decimal integer'

class NonIntScryptMemorySpecifierError(obnamlib.ObnamError):

    msg = 'Scrypt memory amount is not a decimal integer'

class ScryptMemoryTooSmallError(obnamlib.ObnamError):

    msg = 'Scrypt memory amount must be at least 16 megabytes'

class ScryptMemoryNotPowerOfTwoError(obnamlib.ObnamError):

    msg = 'Scrypt memory amount must be a power of two'

class ZeroScryptWorkMultiplierError(obnamlib.ObnamError):

    msg = 'Scrypt work multiplier must not be zero'

class ScryptSaltNotValidBase64Error(obnamlib.ObnamError):

    msg = 'Scrypt salt is not a valid base64 string'

class BadScryptSaltLengthError(obnamlib.ObnamError):

    msg = 'Wrong length for scrypt salt (must be 32 bytes)'

class PassPhraseTooShortError(obnamlib.ObnamError):

    msg = 'The pass phrase is too short (must be at least 12 bytes)'

class KeyNotValidBase64Error(obnamlib.ObnamError):

    msg = 'The key is not a valid base64 string'

class TopLevelDecryptionFailedError(obnamlib.ObnamError):

    msg = ('Decryption with the current client key failed '
           '(either wrong key or corrupt repository)')

class LeafDecryptionFailedError(obnamlib.ObnamError):

    msg = 'Decryption failed; repository corrupted'

class GpgKeySpecifiedError(obnamlib.ObnamError):

    msg = 'Both GPG key and XSalsa20 key specified; using both not supported'

class BadSalsaKeyLengthError(obnamlib.ObnamError):

    msg = 'Wrong length for XSalsa20 key (must be 32 bytes)'

class BadToplevelSalsaKeyLengthError(obnamlib.ObnamError):

    msg = 'Wrong length for stored intermediate key; repository tampered with'

class SalsaPlugin(obnamlib.ObnamPlugin):
    '''Plug-in for encryption using the NaCl/libsodium secret_box construction
    (XSalsa20+Poly1305).

    The client key can be hard-coded into Obnam's configuration, read from
    stdin or derived from an interactively-entered pass phrase.

    All clients use the same 256-bit client key. This key is used to encrypt
    further keys that are stored in the repo and are used to encrypt the
    repository data. This allows the client key to be changed without
    re-encrypting the entire repository.

    Both levels of encryption use XSalsa20+Poly1305. This is expected to be
    post-quantum-resistant on the 128-bit level of security. Note that while
    the GPG encryption plug-in uses per-client keys (non-quantum-resistant)
    asymmetric cryptography for the first level, it still requires the clients
    to be mutually-trusting as far as the chunk data goes. By extending the
    mutual-trust requirement from the chunk data to metadata, this plug-in
    gains simplicity and (as currently conjectured) post-quantum resistance.

    '''

    def enable(self):
        salsa_group = obnamlib.option_group['salsa'] = 'Encryption with XSalsa20'

        self.app.settings.string(
            ['salsa-key'],
            'The current 32-byte client key encoded as base64 or the word '
            '"stdin" to read a base64-encoded 32-byte key followed by a line '
            'feed from standard input or "tty-scrypt:M:W:BASE64" to use the '
            'libsodium flavor of scrypt to derive the key from a pass phrase '
            'read from the tty where M is the amount of memory to use for '
            'scrypt key derivation in megabytes (must be a power of two and '
            'greater than or equal to 16), W is a work multiplier (positive '
            'integer; 1 means the libsodium baseline recommendation for M '
            'amount of memory, 2 means twice that, etc.) and BASE64 is 32-byte '
            'salt encoded as base64. ',
            group=salsa_group)

        self.app.settings.string(
            ['salsa-new-key'],
            'The new 32-byte client key encoded as base64 or the word '
            '"stdin" or "tty-scrypt:M:W:BASE64" (see the description of '
            '"salsa-key" for what these mean).',
            group=salsa_group)

        self.tag = "s"

        hooks = [
            ('repository-toplevel-init', self.toplevel_init,
             obnamlib.Hook.DEFAULT_PRIORITY),
            ('repository-data', self,
             obnamlib.Hook.LATE_PRIORITY),
        ]
        for name, callback, rev in hooks:
            self.app.hooks.add_callback(name, callback, rev)

        self._key = None

        self.app.add_subcommand('change-salsa-key', self.change_key)

        self._symkeys = obnamlib.SymmetricKeyCache()

    def disable(self):
        self._symkeys.clear()

    def _parse_non_negative_integer(self, input, is_ops):
        if len(input) == 0:
            if is_ops:
                raise EmptyScryptWorkMultiplierError()
            else:
                raise EmptyScryptMemoryError()
        for c in input:
            if not (c >= '0' and c <= '9'):
                if is_ops:
                    raise NonIntScryptOperationSpecifierError()
                else:
                    raise NonIntEmptyScryptMemoryError()
        return int(input)

    def _get_key(self, new_key=False):
        b64 = self.app.settings['salsa-new-key' if new_key else 'salsa-key']
        if not b64:
            return None
        if b64.startswith("tty-scrypt:"):
            parts = b64.split(":")
            if len(parts) != 4:
                raise WrongNumberOfScryptComponentsError()
            memory = self._parse_non_negative_integer(parts[1], False)
            if memory < 16:
                raise ScryptMemoryTooSmallError()
            if (memory & (memory - 1)) != 0:
                raise ScryptMemoryNotPowerOfTwoError()
            factor = self._parse_non_negative_integer(parts[2], True)
            if factor == 0:
                raise ZeroScryptWorkMultiplierError()
            mem_limit = memory * 1024 * 1024
            ops_limit = (mem_limit / 32) * factor
            salt = None
            try:
                salt = base64.b64decode(parts[3])
            except:
                raise ScryptSaltNotValidBase64Error()
            if len(salt) != pysodium.crypto_pwhash_scryptsalsa208sha256_SALTBYTES:
                raise BadScryptSaltLengthError()
            if new_key:
                print "Please enter the new pass phrase:"
            else:
                print "Please enter the current pass phrase:"              
            curses.noecho()
            passwd = sys.stdin.readline().rstrip('\n\r')
            curses.echo()
            # The length check is arbitrary
            if len(passwd) < 12:
                raise PassPhraseTooShortError()
            try:
                return pysodium.crypto_pwhash_scryptsalsa208sha256(
                    pysodium.crypto_secretbox_KEYBYTES,
                    passwd,
                    salt,
                    ops_limit,
                    mem_limit)
            except:
                raise 
        if b64 == 'stdin':
            b64 = sys.stdin.readline()
        key = None
        try:
            key = base64.b64decode(b64)
        except:
            raise KeyNotValidBase64Error()
        if len(key) != pysodium.crypto_secretbox_KEYBYTES:
            raise BadSalsaKeyLengthError()
        return key

    @property
    def key(self):
        if not self._key:
            self._key = self._get_key()
        return self._key

    def _write_file(self, repo, pathname, contents):
        repo.get_fs().write_file(pathname, contents)

    def _generate_key(self):
        return pysodium.randombytes(pysodium.crypto_secretbox_KEYBYTES)

    def _encrypt(self, cleartext, key):
        # XSalsa20 (in use here) is the extended-nonce variant of Salsa20. The
        # extended nonce is 192 bits long. To quote NaCl documentation for
        # secretbox: "Nonces are long enough that randomly generated nonces have
        # negligible risk of collision." Hence, we use randomly-generated
        # nonces.
        #
        # Storing a nonce counter in the repo would not be appropriate, since
        # the adversary could roll the repo back to a previous state and
        # cause nonce reuse that way. Storing a nonce counter on the client
        # is not appropriate, since the premise of a backup program is that
        # the local storage may be lost. (Losing a local nonce counter would
        # allow for subsequent reads, though.)
        nonce = pysodium.randombytes(pysodium.crypto_secretbox_NONCEBYTES)
        return nonce + pysodium.crypto_secretbox(cleartext, nonce, key)

    def _decrypt(self, ciphertext, key, is_toplevel=False):
        try:
            return pysodium.crypto_secretbox_open(
            ciphertext[pysodium.crypto_secretbox_NONCEBYTES:],
            ciphertext[0:pysodium.crypto_secretbox_NONCEBYTES],
            key)
        except ValueError:
            if is_toplevel:
                raise TopLevelDecryptionFailedError()
            else:
                raise LeafDecryptionFailedError()
 
    def toplevel_init(self, repo, toplevel):
        '''Initialize a new toplevel for encryption.'''

        if not self.key:
            return

        # Double encryption or migrating between encryption methods not
        # supported.
        if self.app.settings['encrypt-with']:
            raise GpgKeySpecifiedError()

        toplevel_key = self._generate_key()
        encrypted = self._encrypt(toplevel_key, self.key)
        self._write_file(repo, os.path.join(toplevel, 'key'), encrypted)

        # Not writing a separate "userkeys" file, since the clients need to
        # be mutually trusting anyway.

    def filter_read(self, encrypted, repo, toplevel):
        return self._decrypt(encrypted, self._get_toplevel_key(repo, toplevel))

    def filter_write(self, cleartext, repo, toplevel):
        if not self.key:
            return cleartext
        return self._encrypt(cleartext, self._get_toplevel_key(repo, toplevel))

    def _get_toplevel_key(self, repo, toplevel):
        key = self._symkeys.get(repo, toplevel)
        if key is None:
            encrypted = repo.get_fs().cat(os.path.join(toplevel, 'key'))
            key = self._decrypt(encrypted, self.key, True)
            if len(key) != pysodium.crypto_secretbox_KEYBYTES:
                # This error situation should be possible only if whoever has
                # tampered with the repo holds the correct client key, but
                # let's have this check anyway.
                raise BadToplevelSalsaKeyLengthError()
            self._symkeys.put(repo, toplevel, key)
        return key

    def _quit_if_unencrypted(self):
        if self.app.settings['salsa-key']:
            return False
        self.app.output.write('Warning: XSalsa20 encryption not in use.\n')
        self.app.output.write('(Use --salsa-key to set the current key.)\n')
        return True

    def _find_clientdirs(self, repo, client_names):
        return [repo.get_client_extra_data_directory(client_name)
                for client_name in client_names]

    def _rewrite_toplevel_key(self, repo, toplevel, new_key):
        toplevel_key = self._get_toplevel_key(repo, toplevel)
        userkeys = self.read_keyring(repo, toplevel)
        encrypted = self._encrypt(toplevel_key, new_key)
        self._overwrite_file(repo, os.path.join(toplevel, 'key'), encrypted)

    def change_key(self, client_names):
        '''Change the XSalsa20 key for the repository.'''
        if self._quit_if_unencrypted():
            return
        self.app.settings.require('salsa-new-key')
        repo = self.app.get_repository_object()
        new_key = self._get_key(True)
        key = obnamlib.get_public_key(keyid)
        clients = self._find_clientdirs(repo, client_names)
        for toplevel in repo.get_shared_directories() + clients:
            self.add_to_userkeys(repo, toplevel, key)
            self.rewrite_symmetric_key(repo, toplevel)

