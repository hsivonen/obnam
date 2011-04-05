# Copyright (C) 2011  Lars Wirzenius
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

import obnamlib


class EncryptionPlugin(obnamlib.ObnamPlugin):

    def enable(self):
        self.app.config.new_string(['encrypt-with'],
                                   'PGP key with which to encrypt data '
                                        'in the backup repository')
        
        hooks = [
            ('repository-toplevel-init', self.toplevel_init),
            ('repository-read-data', self.toplevel_read_data),
            ('repository-write-data', self.toplevel_write_data),
        ]
        for name, callback in hooks:
            self.app.hooks.add_callback(name, callback)
            
        self._pubkey = None

    @property
    def keyid(self):
        return self.app.config['encrypt-with']
        
    @property
    def pubkey(self):
        if self._pubkey is None:
            self._pubkey = obnamlib.get_public_key(self.keyid)
        return self._pubkey

    def toplevel_init(self, repo, toplevel):
        '''Initialize a new toplevel for encryption.'''
        
        if not self.keyid:
            return
        
        pubkeys = obnamlib.Keyring()
        pubkeys.add(self.pubkey)

        symmetric_key = obnamlib.generate_symmetric_key()
        encrypted = obnamlib.encrypt_with_keyring(symmetric_key, pubkeys)
        repo.fs.write_file(os.path.join(toplevel, 'key'), encrypted)

        encoded = str(pubkeys)
        encrypted = obnamlib.encrypt_symmetric(encoded, symmetric_key)
        repo.fs.write_file(os.path.join(toplevel, 'userkeys'), encrypted)

    def toplevel_read_data(self, encrypted, repo, toplevel):
        if not self.keyid:
            return encrypted
        symmetric_key = self.get_symmetric_key(repo, toplevel)
        return obnamlib.decrypt_with_symmetric_key(encrypted, symmetric_key)

    def toplevel_write_data(self, cleartext, repo, toplevel):
        if not self.keyid:
            return cleartext
        symmetric_key = self.get_symmetric_key(repo, toplevel)
        return obnamlib.encrypt_with_symmetric_key(cleartext, symmetric_key)

    def get_symmetric_key(self, repo, toplevel):
        encoded = repo.fs.cat(os.path.join(toplevel, 'key'))
        return obnamlib.decrypt_with_secret_keys(encoded)

    def read_keyring(self, repo, toplevel):
        encrypted = repo.fs.cat(os.path.join(toplevel, 'userkeys'))
        encoded = self.toplevel_read_data(encrypted, repo, toplevel)
        return obnamlib.Keyring(encoded=encoded)

    def write_keyring(self, repo, toplevel, keyring):
        encoded = str(keyring)
        encrypted = self.toplevel_write_data(encoded, repo, toplevel)
        pathname = os.path.join(toplevel, 'userkeys')
        repo.fs.overwrite_file(pathname, encrypted)

    def add_to_userkeys(self, repo, toplevel, public_key):
        userkeys = self.read_keyring(repo, toplevel)
        userkeys.add(public_key)
        self.write_keyring(repo, toplevel, userkeys)

    def remove_from_userkeys(self, repo, toplevel, keyid):
        userkeys = self.read_keyring(repo, toplevel)
        if keyid in userkeys:
            userkeys.remove(keyid)
            self.write_keyring(repo, toplevel, userkeys)

    def add_client(self, repo, client_public_key):
        self.add_to_userkeys(repo, 'metadata', client_public_key)
        self.add_to_userkeys(repo, 'clientlist', client_public_key)
        self.add_to_userkeys(repo, 'chunks', client_public_key)
        self.add_to_userkeys(repo, 'chunksums', client_public_key)
        # client will add itself to the clientlist and create its own toplevel

    def remove_client(self, repo, client_keyid):
        # client may remove itself, since it has access to the symmetric keys
        # we assume the client-specific toplevel has already been removed
        self.remove_from_userkeys(repo, 'chunksums', client_keyid)
        self.remove_from_userkeys(repo, 'chunks', client_keyid)
        self.remove_from_userkeys(repo, 'clientlist', client_keyid)
        self.remove_from_userkeys(repo, 'metadata', client_keyid)

