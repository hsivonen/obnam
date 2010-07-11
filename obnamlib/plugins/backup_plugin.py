# Copyright (C) 2009, 2010  Lars Wirzenius
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
import re
import stat

import obnamlib


class BackupPlugin(obnamlib.ObnamPlugin):

    def enable(self):
        self.app.register_command('backup', self.backup)
        self.app.config.new_list(['root'], 'what to backup')
        self.app.config.new_list(['exclude'], 
                                 'regular expression for pathnames to '
                                 'exclude from backup (can be used multiple '
                                 'times)')
        self.app.config.new_processed(['checkpoint'],
                                      'make a checkpoint after a given size, '
                                      'default unit is MiB (%default)',
                                      self.parse_checkpoint_size)
        self.app.config['checkpoint'] = '1 GiB'

    def parse_checkpoint_size(self, value):
        p = obnamlib.ByteSizeParser()
        p.set_default_unit('MiB')
        return p.parse(value)
        
    def backup(self, args):
        logging.debug('backup starts')
        logging.debug('checkpoints every %s' % self.app.config['checkpoint'])

        self.app.config.require('store')
        self.app.config.require('hostname')

        roots = self.app.config['root'] + args
        logging.debug('backup roots: %s' % roots)

        storepath = self.app.config['store']
        logging.debug('store: %s' % storepath)
        storefs = self.app.fsf.new(storepath)
        storefs.connect()
        self.store = obnamlib.Store(storefs, self.app.config['node-size'],
                                    self.app.config['upload-queue-size'])

        hostname = self.app.config['hostname']
        logging.debug('hostname: %s' % hostname)
        if hostname not in self.store.list_hosts():
            logging.debug('adding host %s' % hostname)
            self.store.lock_root()
            self.store.add_host(hostname)
            self.store.commit_root()

        self.store.lock_host(hostname)
        self.store.start_generation()
        self.fs = None
        
        self.exclude_pats = [re.compile(x) for x in self.app.config['exclude']]

        for root in roots:
            if not self.fs:
                self.fs = self.app.fsf.new(root)
                self.fs.connect()
            else:
                self.fs.reinit(root)
            absroot = self.fs.abspath('.')
            for pathname, metadata in self.find_files(absroot):
                logging.debug('backing up %s' % pathname)
                try:
                    self.backup_metadata(pathname, metadata)
                    if stat.S_ISDIR(metadata.st_mode):
                        self.backup_dir_contents(pathname)
                    elif stat.S_ISREG(metadata.st_mode):
                        self.backup_file_contents(pathname)
                except OSError, e:
                    logging.error('Could not back up %s: %s' % 
                                  (pathname, e.strerror))
                    self.app.hooks.call('error-message', 
                                        'Could not back up %s: %s' %
                                        (pathname, e.strerror))
                if storefs.bytes_written >= self.app.config['checkpoint']:
                    logging.debug('Making checkpoint')
                    self.backup_parents('.')
                    self.store.commit_host(checkpoint=True)
                    self.store.lock_host(hostname)
                    self.store.start_generation()
                    storefs.bytes_written = 0

            self.backup_parents('.')

        if self.fs:
            self.fs.close()
        self.store.commit_host()
        storefs.close()

        logging.debug('backup finished')

    def find_files(self, root):
        '''Find all files and directories that need to be backed up.
        
        This is a generator.
        
        The caller should not recurse through directories, just backup
        the directory itself (name, metadata, file list).
        
        '''

        generator = self.fs.depth_first(root, prune=self.prune)
        for dirname, subdirs, basenames in generator:
            needed = False
            for basename in basenames:
                pathname = os.path.join(dirname, basename)
                metadata = obnamlib.read_metadata(self.fs, pathname)
                self.app.hooks.call('progress-found-file', pathname, metadata)
                if self.needs_backup(pathname, metadata):
                    yield pathname, metadata
                    needed = True
            metadata = obnamlib.read_metadata(self.fs, dirname)
            if needed or self.needs_backup(dirname, metadata):
                yield dirname, metadata

    def prune(self, dirname, subdirs, filenames):
        '''Remove unwanted things.'''

        def prune_list(items):
            delete = []
            for pat in self.exclude_pats:
                for item in items:
                    path = os.path.join(dirname, item)
                    if pat.search(path):
                        delete.append(item)
            for path in delete:
                i = items.index(path)
                del items[i]
            
        prune_list(subdirs)
        prune_list(filenames)

    def needs_backup(self, pathname, current):
        '''Does a given file need to be backed up?'''
        
        try:
            old = self.store.get_metadata(self.store.new_generation, pathname)
        except obnamlib.Error:
            # File does not exist in the previous generation, so it
            # does need to be backed up.
            return True
        return (current.st_mtime != old.st_mtime or
                current.st_mode != old.st_mode or
                current.st_nlink != old.st_nlink or
                current.st_size != old.st_size or
                current.st_uid != old.st_uid or
                current.st_gid != old.st_gid)

    def backup_parents(self, root):
        '''Back up parents of root, non-recursively.'''
        root = self.fs.abspath(root)
        logging.debug('backing up parents of %s' % root)
        while True:
            parent = os.path.dirname(root)
            metadata = obnamlib.read_metadata(self.fs, root)
            self.store.create(root, metadata)
            if root == parent:
                break
            root = parent

    def backup_metadata(self, pathname, metadata):
        '''Back up metadata for a filesystem object'''
        
        logging.debug('backup_metadata: %s' % pathname)
        self.store.create(pathname, metadata)

    def backup_file_contents(self, filename):
        '''Back up contents of a regular file.'''
        logging.debug('backup_file_contents: %s' % filename)
        chunkids = []
        cgids = []
        groupsum = self.store.new_checksummer()
        f = self.fs.open(filename, 'r')
        chunk_size = int(self.app.config['chunk-size'])
        chunk_group_size = int(self.app.config['chunk-group-size'])
        while True:
            data = f.read(chunk_size)
            if not data:
                break
            chunkids.append(self.backup_file_chunk(data))
            groupsum.update(data)
            if len(chunkids) == chunk_group_size:
                checksum = groupsum.hexdigest()
                cgid = self.store.put_chunk_group(chunkids, checksum)
                cgids.append(cgid)
                chunkids = []
                groupsum = self.store.new_checksummer()
            self.app.hooks.call('progress-data-uploaded', len(data))
        f.close()
        
        if cgids:
            if chunkids:
                checksum = groupsum.hexdigest()
                cgid = self.store.put_chunk_group(chunkids, checksum)
                cgids.append(cgid)
            self.store.set_file_chunk_groups(filename, cgids)
        else:
            self.store.set_file_chunks(filename, chunkids)

    def backup_file_chunk(self, data):
        '''Back up a chunk of data by putting it into the store.'''
        checksum = self.store.checksum(data)
        existing = self.store.find_chunks(checksum)
        if existing:
            chunkid = existing[0]
        else:
            chunkid = self.store.put_chunk(data, checksum)
        return chunkid

    def backup_dir_contents(self, root):
        '''Back up the list of files in a directory.'''

        logging.debug('backup_dir: %s' % root)

        new_basenames = self.fs.listdir(root)
        try:
            old_basenames = self.store.listdir(self.store.new_generation, 
                                               root)
        except obnamlib.Error:
            old_basenames = []

        for old in old_basenames:
            if old not in new_basenames:
                self.store.remove(os.path.join(root, old))
        # Files that are created after the previous generation will be
        # added to the directory when they are backed up, so we don't
        # need to worry about them here.
