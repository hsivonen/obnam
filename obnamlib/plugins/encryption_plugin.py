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


import logging
import os

import obnamlib


class EncryptionPlugin(obnamlib.ObnamPlugin):

    symmetric_key_bits = 256

    def enable(self):
        self.app.config.new_string(['encrypt-with'],
                                   'PGP key with which to encrypt data '
                                        'in the backup repository')
        self.app.config.new_string(['keyid'],
                                   'PGP key id to add to/remove from '
                                        'the backup repository')
        self.app.config.new_boolean(['weak-random'],
                                    'use /dev/urandom instead of /dev/random '
                                        'to generate symmetric keys')
        
        hooks = [
            ('repository-toplevel-init', self.toplevel_init),
            ('repository-read-data', self.toplevel_read_data),
            ('repository-write-data', self.toplevel_write_data),
            ('repository-add-client', self.add_client),
        ]
        for name, callback in hooks:
            self.app.hooks.add_callback(name, callback)
            
        self._pubkey = None
        
        self.app.register_command('client-keys', self.client_keys)
        self.app.register_command('list-keys', self.list_keys)
        self.app.register_command('list-toplevels', self.list_toplevels)
        self.app.register_command('add-key', self.add_key)
        self.app.register_command('remove-key', self.remove_key)
        self.app.register_command('remove-client', self.remove_client)
        
        self._cached_keys = dict()
        self._cached_repo = None
        
    def disable(self):
        self._cached_keys = dict()
        self._cached_repo = None

    @property
    def keyid(self):
        return self.app.config['encrypt-with']
        
    @property
    def pubkey(self):
        if self._pubkey is None:
            self._pubkey = obnamlib.get_public_key(self.keyid)
        return self._pubkey
        
    @property
    def devrandom(self):
        if self.app.config['weak-random']:
            return '/dev/urandom'
        else:
            return '/dev/random'

    def toplevel_init(self, repo, toplevel):
        '''Initialize a new toplevel for encryption.'''
        
        if not self.keyid:
            return
        
        pubkeys = obnamlib.Keyring()
        pubkeys.add(self.pubkey)

        symmetric_key = obnamlib.generate_symmetric_key(
                                self.symmetric_key_bits,
                                filename=self.devrandom)
        encrypted = obnamlib.encrypt_with_keyring(symmetric_key, pubkeys)
        repo.fs.fs.write_file(os.path.join(toplevel, 'key'), encrypted)

        encoded = str(pubkeys)
        encrypted = obnamlib.encrypt_symmetric(encoded, symmetric_key)
        repo.fs.fs.write_file(os.path.join(toplevel, 'userkeys'), encrypted)

    def toplevel_read_data(self, encrypted, repo, toplevel):
        if not self.keyid:
            return encrypted
        symmetric_key = self.get_symmetric_key(repo, toplevel)
        return obnamlib.decrypt_symmetric(encrypted, symmetric_key)

    def toplevel_write_data(self, cleartext, repo, toplevel):
        if not self.keyid:
            return cleartext
        symmetric_key = self.get_symmetric_key(repo, toplevel)
        return obnamlib.encrypt_symmetric(cleartext, symmetric_key)

    def _get_cached_key(self, repo, toplevel):
        if self._cached_repo == repo:
            return self._cached_keys.get(toplevel, None)
        else:
            return None

    def _put_cached_key(self, repo, toplevel, key):
        if self._cached_repo is None or self._cached_repo == repo:
            self._cached_keys[toplevel] = key

    def get_symmetric_key(self, repo, toplevel):
        key = self._get_cached_key(repo, toplevel)
        if key is None:
            encoded = repo.fs.fs.cat(os.path.join(toplevel, 'key'))
            key = obnamlib.decrypt_with_secret_keys(encoded)
            self._put_cached_key(repo, toplevel, key)
        return key

    def read_keyring(self, repo, toplevel):
        encrypted = repo.fs.fs.cat(os.path.join(toplevel, 'userkeys'))
        encoded = self.toplevel_read_data(encrypted, repo, toplevel)
        return obnamlib.Keyring(encoded=encoded)

    def write_keyring(self, repo, toplevel, keyring):
        encoded = str(keyring)
        encrypted = self.toplevel_write_data(encoded, repo, toplevel)
        pathname = os.path.join(toplevel, 'userkeys')
        repo.fs.fs.overwrite_file(pathname, encrypted)

    def add_to_userkeys(self, repo, toplevel, public_key):
        userkeys = self.read_keyring(repo, toplevel)
        userkeys.add(public_key)
        self.write_keyring(repo, toplevel, userkeys)

    def remove_from_userkeys(self, repo, toplevel, keyid):
        userkeys = self.read_keyring(repo, toplevel)
        if keyid in userkeys:
            logging.debug('removing key %s from %s' % (keyid, toplevel))
            userkeys.remove(keyid)
            self.write_keyring(repo, toplevel, userkeys)
        else:
            logging.debug('unable to remove key %s from %s (not there)' %
                          (keyid, toplevel))

    def add_client(self, clientlist, client_name):
        clientlist.set_client_keyid(client_name, self.keyid)

    def client_keys(self, args):
        repo = self.app.open_repository()
        clients = repo.list_clients()
        for client in clients:
            keyid = repo.clientlist.get_client_keyid(client)
            if keyid is None:
                keyid = 'no key'
            print client, keyid

    def _find_keys_and_toplevels(self, repo):
        toplevels = repo.fs.listdir('.')
        keys = dict()
        tops = dict()
        for toplevel in toplevels:
            userkeys = self.read_keyring(repo, toplevel)
            for keyid in userkeys.keyids():
                keys[keyid] = keys.get(keyid, []) + [toplevel]
                tops[toplevel] = tops.get(toplevel, []) + [keyid]
        return keys, tops

    def list_keys(self, args):
        repo = self.app.open_repository()
        keys, tops = self._find_keys_and_toplevels(repo)
        for keyid in keys:
            print 'key: %s' % keyid
            for toplevel in keys[keyid]:
                print '  %s' % toplevel

    def list_toplevels(self, args):
        repo = self.app.open_repository()
        keys, tops = self._find_keys_and_toplevels(repo)
        for toplevel in tops:
            print 'toplevel: %s' % toplevel
            for keyid in tops[toplevel]:
                print '  %s' % keyid

    _shared = ['chunklist', 'chunks', 'chunksums', 'clientlist', 'metadata']
    
    def _find_clientdirs(self, repo, client_names):
        return [repo.client_dir(repo.clientlist.get_client_id(x))
                 for x in client_names]

    def add_key(self, args):
        self.app.config.require('keyid')
        repo = self.app.open_repository()
        keyid = self.app.config['keyid']
        key = obnamlib.get_public_key(keyid)
        clients = self._find_clientdirs(repo, args)
        for toplevel in self._shared + clients:
            self.add_to_userkeys(repo, toplevel, key)

    def remove_key(self, args):
        self.app.config.require('keyid')
        repo = self.app.open_repository()
        keyid = self.app.config['keyid']
        clients = self._find_clientdirs(repo, args)
        for toplevel in self._shared + clients:
            self.remove_from_userkeys(repo, toplevel, keyid)

    def remove_client(self, args):
        repo = self.app.open_repository()
        repo.lock_root()
        for client_name in args:
            logging.info('removing client %s' % client_name)
            repo.remove_client(client_name)
        repo.commit_root()
