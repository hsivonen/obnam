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


import gc
import logging
import os
import re
import stat
import tracing

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
        logging.info('Backup starts')

        logging.info('Checkpoints every %s bytes' % 
                        self.app.config['checkpoint'])

        self.app.config.require('store')
        self.app.config.require('client-name')

        roots = self.app.config['root'] + args

        storepath = self.app.config['store']
        storefs = self.app.fsf.new(storepath, create=True)
        storefs.connect()
        self.store = obnamlib.Store(storefs, self.app.config['node-size'],
                                    self.app.config['upload-queue-size'],
                                    self.app.config['lru-size'])

        client_name = self.app.config['client-name']
        if client_name not in self.store.list_clients():
            tracing.trace('adding new client %s' % client_name)
            self.store.lock_root()
            self.store.add_client(client_name)
            self.store.commit_root()

        self.store.lock_client(client_name)
        self.store.start_generation()
        self.fs = None
        
        self.exclude_pats = [re.compile(x) for x in self.app.config['exclude']]

        last_checkpoint = 0
        self.memory_dump_counter = 0
        interval = self.app.config['checkpoint']

        if roots:
            self.fs = self.app.fsf.new(roots[0])
            self.fs.connect()

            absroots = []
            for root in roots:
                self.fs.reinit(root)
                absroots.append(self.fs.abspath('.'))
                
            self.remove_old_roots(absroots)

            for absroot in absroots:
                logging.info('Backing up root %s' % absroot)
                self.fs.reinit(absroot)
                for pathname, metadata in self.find_files(absroot):
                    tracing.trace('Backing up %s', pathname)
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
                    if storefs.bytes_written - last_checkpoint >= interval:
                        logging.info('Making checkpoint')
                        self.backup_parents('.')
                        self.store.commit_client(checkpoint=True)
                        self.store.lock_client(client_name)
                        self.store.start_generation()
                        last_checkpoint = storefs.bytes_written
                        self.dump_memory_profile('at end of checkpoint')

                self.backup_parents('.')

            if self.fs:
                self.fs.close()

        self.store.commit_client()
        storefs.close()

        logging.info('Backup finished.')
        self.dump_memory_profile('at end of backup run')

    def vmrss(self):
        f = open('/proc/self/status')
        rss = 0
        for line in f:
            if line.startswith('VmRSS'):
                rss = line.split()[1]
        f.close()
        return rss

    def dump_memory_profile(self, msg):
        kind = self.app.config['dump-memory-profile']
        if kind == 'none':
            return
        logging.debug('dumping memory profiling data: %s' % msg)
        logging.debug('VmRSS: %s KiB' % self.vmrss())
        logging.debug('# objects: %d' % len(gc.get_objects()))
        logging.debug('# garbage: %d' % len(gc.garbage))
        if kind == 'heapy':
            from guppy import hpy
            h = hpy()
            logging.debug('memory profile:\n%s' % h.heap())
        elif kind == 'meliae':
            filename = 'obnam-%d.meliae' % self.memory_dump_counter
            logging.debug('memory profile: see %s' % filename)
            from meliae import scanner
            scanner.dump_all_objects(filename)
            self.memory_dump_counter += 1

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
            if not needed:
                needed = self.needs_backup(dirname, metadata)
            if needed:
                yield dirname, metadata

    def prune(self, dirname, subdirs, filenames):
        '''Remove unwanted things.'''

        def prune_list(items):
            delete = set()
            for pat in self.exclude_pats:
                for item in items:
                    path = os.path.join(dirname, item)
                    if pat.search(path):
                        delete.add(item)
            for path in delete:
                i = items.index(path)
                del items[i]
            items.sort()
            
        prune_list(subdirs)
        prune_list(filenames)

    def needs_backup(self, pathname, current):
        '''Does a given file need to be backed up?'''
        
        # Directories always require backing up so that backup_dir_contents
        # can remove stuff that no longer exists from them.
        if current.isdir():
            return True
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
        tracing.trace('backing up parents of %s', root)
        while True:
            parent = os.path.dirname(root)
            metadata = obnamlib.read_metadata(self.fs, root)
            self.store.create(root, metadata)
            if root == parent:
                break
            root = parent

    def backup_metadata(self, pathname, metadata):
        '''Back up metadata for a filesystem object'''
        
        tracing.trace('backup_metadata: %s', pathname)
        self.store.create(pathname, metadata)

    def backup_file_contents(self, filename):
        '''Back up contents of a regular file.'''
        tracing.trace('backup_file_contents: %s', filename)
        self.store.set_file_chunks(filename, [])
        f = self.fs.open(filename, 'r')
        chunk_size = int(self.app.config['chunk-size'])
        chunkids = []
        while True:
            data = f.read(chunk_size)
            if not data:
                break
            chunkids.append(self.backup_file_chunk(data))
            if len(chunkids) >= obnamlib.DEFAULT_CHUNKIDS_PER_GROUP:
                self.store.append_file_chunks(filename, chunkids)
                self.dump_memory_profile('after appending some chunkids')
                chunkids = []
            self.app.hooks.call('progress-data-uploaded', len(data))
        f.close()
        if chunkids:
            self.store.append_file_chunks(filename, chunkids)
        self.dump_memory_profile('at end of file content backup for %s' %
                                 filename)
        
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

        tracing.trace('backup_dir: %s', root)

        new_basenames = self.fs.listdir(root)
        old_basenames = self.store.listdir(self.store.new_generation, 
                                           root)

        for old in old_basenames:
            pathname = os.path.join(root, old)
            if old not in new_basenames:
                self.store.remove(pathname)
        # Files that are created after the previous generation will be
        # added to the directory when they are backed up, so we don't
        # need to worry about them here.

    def remove_old_roots(self, new_roots):
        '''Remove from started generation anything that is not a backup root.
        
        We recurse from filesystem root directory until getting to one of 
        the new backup roots, or a directory or file that is not a parent 
        of one of the new backup roots. We remove anything that is not a
        new backup root, or their parent.
        
        '''
        
        def is_parent(pathname):
            x = pathname + os.sep
            for new_root in new_roots:
                if new_root.startswith(x):
                    return True
            return False

        def helper(dirname):
            gen_id = self.store.new_generation
            basenames = self.store.listdir(gen_id, dirname)
            for basename in basenames:
                pathname = os.path.join(dirname, basename)
                if is_parent(pathname):
                    metadata = self.store.get_metadata(gen_id, pathname)
                    if metadata.isdir():
                        helper(pathname)
                elif pathname not in new_roots:
                    self.store.remove(pathname)

        helper('/')

