# Copyright (C) 2010  Lars Wirzenius
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


class FsckPlugin(obnamlib.ObnamPlugin):

    def enable(self):
        self.app.register_command('fsck', self.fsck)
        
    def fsck(self, args):
        self.app.config.require('repository')
        logging.debug('fsck on %s' % self.app.config['repository'])
        self.repo = self.app.open_repository()
        self.check_root()

    def check_root(self):
        '''Check the root node.'''
        logging.debug('Checking root node')
        self.app.hooks.call('status', 'Checking root node')
        for client in self.repo.list_clients():
            self.check_client(client)
    
    def check_client(self, client_name):
        '''Check a client.'''
        logging.debug('Checking client %s' % client_name)
        self.app.hooks.call('status', 'Checking client %s' % client_name)
        self.repo.open_client(client_name)
        for genid in self.repo.list_generations():
            self.check_generation(genid)

    def check_generation(self, genid):
        '''Check a generation.'''
        logging.debug('Checking generation %s' % genid)
        self.app.hooks.call('status', 'Checking generation %s' % genid)
        self.check_dir(genid, '/')

    def check_dir(self, genid, dirname):
        '''Check a directory.'''
        logging.debug('Checking directory %s' % dirname)
        self.app.hooks.call('status', 'Checking dir %s' % dirname)
        self.repo.get_metadata(genid, dirname)
        for basename in self.repo.listdir(genid, dirname):
            pathname = os.path.join(dirname, basename)
            metadata = self.repo.get_metadata(genid, pathname)
            if metadata.isdir():
                self.check_dir(genid, pathname)
            else:
                self.check_file(genid, pathname)
                
    def check_file(self, genid, filename):
        '''Check a non-directory.'''
        logging.debug('Checking file %s' % filename)
        self.app.hooks.call('status', 'Checking file %s' % filename)
        metadata = self.repo.get_metadata(genid, filename)
        if metadata.isfile():
            for chunkid in self.repo.get_file_chunks(genid, filename):
                self.check_chunk(chunkid)

    def check_chunk(self, chunkid):
        '''Check a chunk.'''
        logging.debug('Checking chunk %s' % chunkid)
        self.repo.chunk_exists(chunkid)

