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


import obnamlib


class EncryptionPlugin(obnamlib.ObnamPlugin):

    def enable(self):
        return
        
        hooks = [
            ('repository-toplevel-init', self.toplevel_init),
            ('repository-read-data', self.toplevel_read_data),
            ('repository-write-data', self.toplevel_write_data),
        ]
        for name, callback in hooks:
            self.app.hooks.add_callback(name, callback)
            
        self.client_keyid = self.app.config['client-keyid']
        self.client_pubkey = obnamlib.get_public_key(self.client_keyid)

    def toplevel_init(self, name):
        '''Initialize a new toplevel for encryption.'''
        
        pubkeys = obnamlib.Keyring()
        pubkeys.add(self.client_pubkey)

        symmetric_key = obnamlib.generate_symmetric_key()
        encrypted = obnamlib.encrypt_with_keyring(symmetric_key, pubkeys)
        self.repo.fs.write_file(os.path.join(name, 'key'), encrypted)

        encoded = str(pubkeys)
        encrypted = obnamlib.encrypt_symmetric(encoded, symmetric_key)
        self.repo.fs.write_file(os.path.join(name, 'userkeys'), encrypted)

    def get_symmetric_key(self, toplevel):
        encoded = self.repo.fs.cat(os.path.join(toplevel, 'key'))
        return obnamlib.decrypt_with_secret_keys(encoded)

    def toplevel_read_data(self, toplevel, encrypted):
        symmetric_key = self.get_symmetric_key(toplevel)
        return obnamlib.decrypt_with_symmetric_key(encrypted, symmetric_key)

    def toplevel_write_data(self, toplevel, cleartext):
        symmetric_key = self.get_symmetric_key(toplevel)
        return obnamlib.encrypt_with_symmetric_key(cleartext, symmetric_key)

    def read_keyring(self, toplevel):
        encrypted = self.repo.fs.cat(os.path.join(toplevel, 'userkeys'))
        encoded = self.toplevel_read_data(toplevel, encrypted)
        return obnamlib.Keyring(encoded=encoded)

    def write_keyring(self, toplevel, keyring):
        encoded = str(keyring)
        encrypted = self.toplevel_write_data(toplevel, encoded)
        pathname = os.path.join(toplevel, 'userkeys')
        self.repo.fs.overwrite_file(pathname, encrypted)

    def add_to_userkeys(self, toplevel, public_key):
        userkeys = self.read_keyring(toplevel)
        userkeys.add(public_key)
        self.write_keyring(toplevel, userkeys)

    def remove_from_userkeys(self, toplevel, keyid):
        userkeys = self.read_keyring(toplevel)
        if keyid in userkeys:
            userkeys.remove(keyid)
            self.write_keyring(toplevel, userkeys)

    def add_client(self, client_public_key):
        self.add_to_userkeys('metadata', client_public_key)
        self.add_to_userkeys('clientlist', client_public_key)
        self.add_to_userkeys('chunks', client_public_key)
        self.add_to_userkeys('chunksums', client_public_key)
        # client will add itself to the clientlist and create its own toplevel

    def remove_client(self, client_keyid):
        # client may remove itself, since it has access to the symmetric keys
        # we assume the client-specific toplevel has already been removed
        self.remove_from_userkeys('chunksums', client_keyid)
        self.remove_from_userkeys('chunks', client_keyid)
        self.remove_from_userkeys('clientlist', client_keyid)
        self.remove_from_userkeys('metadata', client_keyid)

