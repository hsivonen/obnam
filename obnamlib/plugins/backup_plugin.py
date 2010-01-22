# Copyright (C) 2009  Lars Wirzenius
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
import time

import obnamlib


class BackupPlugin(obnamlib.ObnamPlugin):

    def enable(self):
        self.app.register_command('backup', self.backup)
        self.app.config.new_list(['root'], 'what to backup')
        
    def backup(self, args):
        roots = self.app.config['root'] + args
        fsf = obnamlib.VfsFactory()
        storefs = fsf.new(self.app.config['store'])
        self.store = obnamlib.Store(storefs)
        self.done = 0
        self.total = 0

        self.store.lock_host(self.app.config['hostname'])
        self.store.start_generation()
        self.fs = None
        for root in roots:
            if not self.fs:
                self.fs = fsf.new(root)
                self.fs.connect()
            else:
                self.fs.reinit(root)
            self.backup_something(self.fs.abspath('.'))
            self.backup_parents('.')
        if self.fs:
            self.fs.close()
        self.store.commit_host()

        self.app.hooks.call('progress-found-file', None, 0)

    def backup_parents(self, root):
        '''Back up parents of root, non-recursively.'''
        root = self.fs.abspath(root)
        while True:
            parent = os.path.dirname(root)
            metadata = obnamlib.read_metadata(self.fs, root)
            self.store.create(root, metadata)
            if root == parent:
                break
            root = parent

    def backup_something(self, root):
        if self.fs.isdir(root):
            self.backup_dir(root)
        else:
            self.backup_file(root)

    def backup_file(self, root):
        '''Back up a non-directory.
        
        If it is a regular file, also back up its contents.
        
        '''
        
        metadata = obnamlib.read_metadata(self.fs, root)
        logging.debug('backup_file: metadata.st_mtime=%s' % repr(metadata.st_mtime))
        self.app.hooks.call('progress-found-file', root, metadata.st_size)
        self.store.create(root, metadata)
        if stat.S_ISREG(metadata.st_mode):
            self.backup_file_contents(root)

    def backup_file_contents(self, filename):
        '''Back up contents of a regular file.'''
        chunkids = []
        f = self.fs.open(filename, 'r')
        while True:
            data = f.read(self.app.config['chunk-size'])
            if not data:
                break
            checksum = self.store.checksum(data)
            chunkid = self.store.put_chunk(data, checksum)
            chunkids.append(chunkid)
            self.app.hooks.call('progress-data-done', len(data))
        f.close()
        self.store.set_file_chunks(filename, chunkids)

    def backup_dir(self, root):
        '''Back up a directory, and everything in it.'''
        try:
            self.store.get_metadata(self.store.new_generation, root)
        except obnamlib.Error:
            pass
        else:
            self.store.remove(root)
        metadata = obnamlib.read_metadata(self.fs, root)
        self.store.create(root, metadata)
        for basename in self.fs.listdir(root):
            fullname = os.path.join(root, basename)
            self.backup_something(fullname)