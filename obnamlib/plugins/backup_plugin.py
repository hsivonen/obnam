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
import traceback
import tracing

import obnamlib


class BackupPlugin(obnamlib.ObnamPlugin):

    def enable(self):
        self.app.add_subcommand('backup', self.backup)
        self.app.settings.string_list(['root'], 'what to backup')
        self.app.settings.string_list(['exclude'], 
                                 'regular expression for pathnames to '
                                 'exclude from backup (can be used multiple '
                                 'times)')
        self.app.settings.boolean(['exclude-caches'],
                                    'exclude directories (and their subdirs) '
                                    'that contain a CACHEDIR.TAG file')
        self.app.settings.boolean(['one-file-system'],
                                    'exclude directories (and their subdirs) '
                                    'that are in a different filesystem')
        self.app.settings.bytesize(['checkpoint'],
                                      'make a checkpoint after a given SIZE '
                                      '(%default)',
                                    metavar='SIZE',
                                    default=1024**3)
        self.app.settings.integer(['chunkids-per-group'],
                                  'encode NUM chunk ids per group (%default)',
                                  metavar='NUM',
                                  default=obnamlib.DEFAULT_CHUNKIDS_PER_GROUP)

    def parse_checkpoint_size(self, value):
        p = obnamlib.ByteSizeParser()
        p.set_default_unit('MiB')
        return p.parse(value)
        
    def backup(self, args):
        '''Backup data to repository.'''
        logging.info('Backup starts')
        logging.info('Checkpoints every %s bytes' % 
                        self.app.settings['checkpoint'])

        self.app.settings.require('repository')
        self.app.settings.require('client-name')

        self.compile_exclusion_patterns()
        self.memory_dump_counter = 0

        self.repo = self.app.open_repository(create=True)
        client_name = self.app.settings['client-name']
        self.add_client(client_name)

        self.repo.lock_client(client_name)
        try:
            self.repo.start_generation()
            self.fs = None
            roots = self.app.settings['root'] + args
            if roots:
                self.backup_roots(roots)
            self.repo.commit_client()
            self.repo.fs.close()

            logging.info('Backup finished.')
            self.dump_memory_profile('at end of backup run')
        except BaseException:
            logging.info('Unlocking client because of error')
            self.repo.unlock_client()
            raise

    def add_client(self, client_name):
        if client_name not in self.repo.list_clients():
            tracing.trace('adding new client %s' % client_name)
            self.repo.lock_root()
            self.repo.add_client(client_name)
            self.repo.commit_root()

    def compile_exclusion_patterns(self):
        log = self.app.settings['log']
        if log:
            log = self.app.settings['log']
            self.app.settings['exclude'].append(log)
        for pattern in self.app.settings['exclude']:
            logging.debug('Exclude pattern: %s' % pattern)
        self.exclude_pats = [re.compile(x) 
                             for x in self.app.settings['exclude']]

    def vmrss(self):
        f = open('/proc/self/status')
        rss = 0
        for line in f:
            if line.startswith('VmRSS'):
                rss = line.split()[1]
        f.close()
        return rss

    def dump_memory_profile(self, msg):
        kind = self.app.settings['dump-memory-profile']
        if kind == 'none':
            return
        logging.debug('dumping memory profiling data: %s' % msg)
        logging.debug('VmRSS: %s KiB' % self.vmrss())
        if kind in ['heapy', 'meliae']:
            # These are fairly expensive operations, so we only log them
            # if we're doing expensive stuff anyway.
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

    def backup_roots(self, roots):
        self.fs = self.app.fsf.new(roots[0])
        self.fs.connect()

        absroots = []
        for root in roots:
            self.fs.reinit(root)
            absroots.append(self.fs.abspath('.'))
            
        self.remove_old_roots(absroots)

        last_checkpoint = 0
        interval = self.app.settings['checkpoint']

        for root in roots:
            logging.info('Backing up root %s' % root)
            self.fs.reinit(root)
            absroot = self.fs.abspath('.')
            self.root_metadata = self.fs.lstat(absroot)
            for pathname, metadata in self.find_files(absroot):
                logging.debug('Backing up %s' % pathname)
                try:
                    if stat.S_ISDIR(metadata.st_mode):
                        self.backup_dir_contents(pathname)
                    elif stat.S_ISREG(metadata.st_mode):
                        assert metadata.md5 is None
                        metadata.md5 = self.backup_file_contents(pathname)
                    self.backup_metadata(pathname, metadata)
                except OSError, e:
                    msg = 'Can\'t back up %s: %s' % (pathname, e.strerror)
                    logging.error(msg)
                    logging.debug(repr(e))
                    self.app.hooks.call('error-message', msg)
                except IOError, e:
                    msg = 'Can\'t back up %s: %s' % (pathname, e.strerror)
                    logging.error(msg)
                    logging.debug(repr(e))
                    self.app.hooks.call('error-message', msg)
                if self.repo.fs.bytes_written - last_checkpoint >= interval:
                    logging.info('Making checkpoint')
                    self.backup_parents('.')
                    self.repo.commit_client(checkpoint=True)
                    self.repo.lock_client(client_name)
                    self.repo.start_generation()
                    last_checkpoint = self.repo.fs.bytes_written
                    self.dump_memory_profile('at end of checkpoint')

            self.backup_parents('.')

        if self.fs:
            self.fs.close()

    def find_files(self, root):
        '''Find all files and directories that need to be backed up.
        
        This is a generator. It yields (pathname, metadata) pairs.
        
        The caller should not recurse through directories, just backup
        the directory itself (name, metadata, file list).
        
        '''
        for pathname, st in self.fs.scan_tree(root, ok=self.can_be_backed_up):
            tracing.trace('considering %s' % pathname)
            try:
                metadata = obnamlib.read_metadata(self.fs, pathname)
                self.app.hooks.call('progress-found-file', pathname, metadata)
                if self.needs_backup(pathname, metadata):
                    yield pathname, metadata
            except BaseException, e:
                msg = 'Cannot back up %s: %s' % (pathname, str(e))
                logging.error(msg)
                self.app.hooks.call('error-message', msg)

    def can_be_backed_up(self, pathname, st):
        if self.app.settings['one-file-system']:
            if st.st_dev != self.root_metadata.st_dev: 
                logging.info('Excluding (one-file-system): %s' %
                             pathname)
                return False

        for pat in self.exclude_pats:
            if pat.search(pathname):
                logging.info('Excluding (pattern): %s' % pathname)
                return False

        if stat.S_ISDIR(st.st_mode) and self.app.settings['exclude-caches']:
            tag_filename = 'CACHEDIR.TAG'
            tag_contents = 'Signature: 8a477f597d28d172789f06886806bc55'
            tag_path = os.path.join(pathname, 'CACHEDIR.TAG')
            if self.fs.exists(tag_path):
                # Can't use with, because Paramiko's SFTPFile does not work.
                f = self.fs.open(tag_path, 'rb')
                data = f.read(len(tag_contents))
                f.close()
                if data == tag_contents:
                    logging.info('Excluding (cache dir): %s' % pathname)
                    return False
        
        return True

    def needs_backup(self, pathname, current):
        '''Does a given file need to be backed up?'''
        
        # Directories always require backing up so that backup_dir_contents
        # can remove stuff that no longer exists from them.
        if current.isdir():
            return True
        try:
            old = self.repo.get_metadata(self.repo.new_generation, pathname)
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
            self.repo.create(root, metadata)
            if root == parent:
                break
            root = parent

    def backup_metadata(self, pathname, metadata):
        '''Back up metadata for a filesystem object'''
        
        tracing.trace('backup_metadata: %s', pathname)
        self.repo.create(pathname, metadata)

    def backup_file_contents(self, filename):
        '''Back up contents of a regular file.'''
        tracing.trace('backup_file_contents: %s', filename)
        tracing.trace('setting file chunks to empty')
        self.repo.set_file_chunks(filename, [])
        tracing.trace('opening file for reading')
        f = self.fs.open(filename, 'r')
        chunk_size = int(self.app.settings['chunk-size'])
        chunkids = []
        summer = self.repo.new_checksummer()
        while True:
            tracing.trace('reading some data')
            data = f.read(chunk_size)
            if not data:
                tracing.trace('end of data')
                break
            tracing.trace('got %d bytes of data' % len(data))
            summer.update(data)
            chunkids.append(self.backup_file_chunk(data))
            if len(chunkids) >= self.app.settings['chunkids-per-group']:
                tracing.trace('adding %d chunkids to file' % len(chunkids))
                self.repo.append_file_chunks(filename, chunkids)
                self.dump_memory_profile('after appending some chunkids')
                chunkids = []
            self.app.hooks.call('progress-data-uploaded', len(data))
        tracing.trace('closing file')
        f.close()
        if chunkids:
            tracing.trace('adding final %d chunkids to file' % len(chunkids))
            self.repo.append_file_chunks(filename, chunkids)
        self.dump_memory_profile('at end of file content backup for %s' %
                                 filename)
        tracing.trace('done backing up file contents')
        return summer.digest()
        
    def backup_file_chunk(self, data):
        '''Back up a chunk of data by putting it into the repository.'''
        checksum = self.repo.checksum(data)
        existing = self.repo.find_chunks(checksum)
        if existing:
            chunkid = existing[0]
        else:
            chunkid = self.repo.put_chunk(data, checksum)
        return chunkid

    def backup_dir_contents(self, root):
        '''Back up the list of files in a directory.'''

        tracing.trace('backup_dir: %s', root)

        new_basenames = self.fs.listdir(root)
        old_basenames = self.repo.listdir(self.repo.new_generation, root)

        for old in old_basenames:
            pathname = os.path.join(root, old)
            if old not in new_basenames:
                self.repo.remove(pathname)
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
            gen_id = self.repo.new_generation
            basenames = self.repo.listdir(gen_id, dirname)
            for basename in basenames:
                pathname = os.path.join(dirname, basename)
                if is_parent(pathname):
                    metadata = self.repo.get_metadata(gen_id, pathname)
                    if metadata.isdir():
                        helper(pathname)
                elif pathname not in new_roots:
                    self.repo.remove(pathname)

        helper('/')

