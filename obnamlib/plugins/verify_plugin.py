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
import stat

import obnamlib


class VerifyPlugin(obnamlib.ObnamPlugin):

    def enable(self):
        self.app.register_command('verify', self.verify)

    def verify(self, args):
        logging.debug('verifying generation %s' % 
                        self.app.config['generation'])
        if not self.app.config['generation']:
            raise obnamlib.AppException('--generation option must be used '
                                        'with verify')

        if not self.app.config['root']:
            raise obnamlib.AppException('--root option must be used '
                                        'with verify')

        logging.debug('verifying what: %s' % repr(args))
        if not args:
            logging.debug('no args given, so verifying everything')
            args = ['/']
    
        fs = self.app.fsf.new(self.app.config['store'])
        fs.connect()
        self.store = obnamlib.Store(fs)
        self.store.open_host(self.app.config['hostname'])
        self.fs = self.app.fsf.new(self.app.config['root'][0])
        self.fs.connect()
        self.fs.reinit('/')

        gen = self.store.genspec(self.app.config['generation'])
        for arg in args:
            metadata = self.store.get_metadata(gen, arg)
            if metadata.isdir():
                self.verify_recursively(gen, arg)
            else:
                self.verify_file(gen, arg)

    def fail(self, filename, reason):
        logging.error('verify failure for %s: %s' % (filename, reason))
        self.app.hooks.call('error-message',
                            'verify failure: %s: %s' % (filename, reason))

    def verify_recursively(self, gen, root):
        logging.debug('verifying dir %s' % root)
        self.verify_metadata(gen, root)
        for basename in self.store.listdir(gen, root):
            full = os.path.join(root, basename)
            metadata = self.store.get_metadata(gen, full)
            if metadata.isdir():
                self.verify_recursively(gen, full)
            else:
                self.verify_file(gen, full)

    def verify_metadata(self, gen, filename):
        backed_up = self.store.get_metadata(gen, filename)
        live_data = obnamlib.read_metadata(self.fs, filename)
        for field in obnamlib.metadata_verify_fields:
            if getattr(backed_up, field) != getattr(live_data, field):
                self.fail(filename, 'metadata change: %s' % field)

    def verify_file(self, gen, filename):
        self.verify_metadata(gen, filename)
        metadata = self.store.get_metadata(gen, filename)
        if stat.S_ISREG(metadata.st_mode):
            self.verify_regular_file(gen, filename, metadata)
    
    def verify_regular_file(self, gen, filename, metadata):
        logging.debug('verifying regular %s' % filename)
        f = self.fs.open(filename, 'r')

        chunkids = self.store.get_file_chunks(gen, filename)
        if chunkids:
            if not self.verify_chunks(f, chunkids):
                self.fail(filename, 'data changed')
        else:
            cgids = self.store.get_file_chunk_groups(gen, filename)
            for cgid in cgids:
                chunkids = self.store.get_chunk_group(cgid)
                if not self.verify_chunks(f, chunkids):
                    self.fail(filename, 'data changed')

        f.close()

    def verify_chunks(self, f, chunkids):
        for chunkid in chunkids:
            backed_up = self.store.get_chunk(chunkid)
            live_data = f.read(len(backed_up))
            if backed_up != live_data:
                return False
        return True

