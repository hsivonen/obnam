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
import sys

import obnamlib


class Fail(Exception):

    def __init__(self, filename, reason):
        self.filename = filename
        self.reason = reason


class VerifyPlugin(obnamlib.ObnamPlugin):

    def enable(self):
        self.app.register_command('verify', self.verify)

    def verify(self, args):
        self.app.config.require('repository')
        self.app.config.require('client-name')
        self.app.config.require('generation')

        logging.debug('verifying generation %s' % 
                        self.app.config['generation'])
        if not args:
            self.app.config.require('root')
            args = self.app.config['root']
        if not args:
            logging.debug('no roots/args given, so verifying everything')
            args = ['/']
        logging.debug('verifying what: %s' % repr(args))
    
        self.repo = self.app.open_repository()
        self.repo.open_client(self.app.config['client-name'])
        self.fs = self.app.fsf.new(args[0])
        self.fs.connect()
        self.fs.reinit('/')

        self.failed = False
        gen = self.repo.genspec(self.app.config['generation'])
        for arg in args:
            arg = os.path.normpath(arg)
            metadata = self.repo.get_metadata(gen, arg)
            try:
                if metadata.isdir():
                    self.verify_recursively(gen, arg)
                else:
                    self.verify_file(gen, arg)
            except Fail, e:
                self.log_fail(e)

        if self.failed:
            sys.exit(1)
        print "Verify did not find problems."

    def log_fail(self, e):
        logging.error('verify failure for %s: %s' % (e.filename, e.reason))
        self.app.hooks.call('error-message',
                            'verify failure: %s: %s' % 
                            (e.filename, e.reason))
        self.failed = True

    def verify_recursively(self, gen, root):
        logging.debug('verifying dir %s' % root)
        self.verify_metadata(gen, root)
        for basename in self.repo.listdir(gen, root):
            full = os.path.join(root, basename)
            metadata = self.repo.get_metadata(gen, full)
            try:
                if metadata.isdir():
                    self.verify_recursively(gen, full)
                else:
                    self.verify_file(gen, full)
            except Fail, e:
                self.log_fail(e)

    def verify_metadata(self, gen, filename):
        backed_up = self.repo.get_metadata(gen, filename)
        try:
            live_data = obnamlib.read_metadata(self.fs, filename)
        except OSError, e:
            raise Fail(filename, 'missing or inaccessible: %s' % e.strerror)
        for field in obnamlib.metadata_verify_fields:
            if getattr(backed_up, field) != getattr(live_data, field):
                raise Fail(filename, 'metadata change: %s' % field)

    def verify_file(self, gen, filename):
        self.verify_metadata(gen, filename)
        metadata = self.repo.get_metadata(gen, filename)
        if stat.S_ISREG(metadata.st_mode):
            self.verify_regular_file(gen, filename, metadata)
    
    def verify_regular_file(self, gen, filename, metadata):
        logging.debug('verifying regular %s' % filename)
        f = self.fs.open(filename, 'r')

        chunkids = self.repo.get_file_chunks(gen, filename)
        if not self.verify_chunks(f, chunkids):
            raise Fail(filename, 'data changed')

        f.close()

    def verify_chunks(self, f, chunkids):
        for chunkid in chunkids:
            backed_up = self.repo.get_chunk(chunkid)
            live_data = f.read(len(backed_up))
            if backed_up != live_data:
                return False
        return True

