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

class RepoKeyDecryptionFailedError(obnamlib.ObnamError):

    msg = ('Decryption with the current client key failed '
           '(either wrong key or corrupt repository)')

class LeafDecryptionFailedError(obnamlib.ObnamError):

    msg = 'Decryption failed; repository corrupted'

class GpgKeySpecifiedError(obnamlib.ObnamError):

    msg = 'Both GPG key and XSalsa20 key specified; using both not supported'

class BadSalsaKeyLengthError(obnamlib.ObnamError):

    msg = 'Wrong length for XSalsa20 key (must be 32 bytes)'

class BadRepoSalsaKeyLengthError(obnamlib.ObnamError):

    msg = 'Wrong length for stored intermediate key; repository tampered with'

class NoClientKeyError(obnamlib.ObnamError):

    msg = ('Cannot access XSalsa20-encrypted data, because the client key '
           'has not been specified with --salsa-key')

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

        self._repo_key = None

        self._client_key = None

        self.app.add_subcommand('change-salsa-key', self.change_key)

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

    def _get_repo_key(self, repo):
        if self._repo_key:
            return self._repo_key
        fs = repo.get_fs()
        if not fs.exists("salsa_key"):
            return None
        client_key = self._get_client_key()
        if not client_key:
            raise NoClientKeyError()
        encrypted = fs.cat("salsa_key")
        self._repo_key = self._decrypt(encrypted, client_key, True)
        if len(self._repo_key) != pysodium.crypto_secretbox_KEYBYTES:
            # This error situation should be possible only if whoever has
            # tampered with the repo holds the correct client key, but
            # let's have this check anyway.
            self._repo_key = None
            raise BadRepoSalsaKeyLengthError()
        return self._repo_key

    def _get_client_key(self):
        if self._client_key:
            return self._client_key
        self._client_key = self._read_client_key()
        return self._client_key

    def _read_client_key(self, new_key=False):
        b64 = self.app.settings['salsa-new-key' if new_key else 'salsa-key']
        if not b64:
            return None

        # Double encryption or migrating between encryption methods not
        # supported.
        if self.app.settings['encrypt-with']:
            raise GpgKeySpecifiedError()

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

    def _decrypt(self, ciphertext, key, is_repo_key=False):
        try:
            return pysodium.crypto_secretbox_open(
            ciphertext[pysodium.crypto_secretbox_NONCEBYTES:],
            ciphertext[:pysodium.crypto_secretbox_NONCEBYTES],
            key)
        except ValueError:
            if is_repo_key:
                raise RepoKeyDecryptionFailedError()
            else:
                raise LeafDecryptionFailedError()
 
    def toplevel_init(self, repo, toplevel):
        '''Initialize the repo for encryption.

        This method is called for every toplevel instead of the repo itself.
        We use the toplevel hook, because a repo-level hook does not exist.
        '''

        client_key = self._get_client_key()
        if not client_key:
            # XSalsa20 encryption not in use
            return

        repo_key = self._get_repo_key(repo)
        if repo_key:
            # Already initialized
            return

        # This is the first time we are initializing a toplevel, so let's
        # initialize the repo itself.
        repo_key = pysodium.randombytes(pysodium.crypto_secretbox_KEYBYTES)

        encrypted = self._encrypt(repo_key, client_key)
        repo.get_fs().write_file("salsa_key", encrypted)

    def filter_read(self, encrypted, repo, toplevel):
        return self._decrypt(encrypted, self._get_repo_key(repo))

    def filter_write(self, cleartext, repo, toplevel):
        if not self._get_client_key():
            return cleartext
        return self._encrypt(cleartext, self._get_repo_key(repo))

    def _quit_if_unencrypted(self):
        if self.app.settings['salsa-key']:
            return False
        self.app.output.write('Warning: XSalsa20 encryption not in use.\n')
        self.app.output.write('(Use --salsa-key to set the current key.)\n')
        return True

    def change_key(self, client_names):
        '''Change the XSalsa20 key for the repository.'''
        if self._quit_if_unencrypted():
            return
        self.app.settings.require('salsa-new-key')
        repo = self.app.get_repository_object()
        repo_key = self._get_repo_key(repo)
        new_key = self._read_client_key(True)
        encrypted = self._encrypt(repo_key, new_key)
        repo.get_fs().overwrite_file("salsa_key", encrypted)

