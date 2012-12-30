# Copyright (C) 2009, 2010, 2011, 2012  Lars Wirzenius
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


import errno
import gc
import logging
import os
import re
import stat
import sys
import time
import traceback
import tracing
import ttystatus

import obnamlib
import larch


class ChunkidPool(object):

    '''Checksum/chunkid mappings that are pending an upload to shared trees.'''
    
    def __init__(self):
        self.clear()
        
    def add(self, chunkid, checksum):
        if checksum not in self._mapping:
            self._mapping[checksum] = []
        self._mapping[checksum].append(chunkid)

    def __contains__(self, checksum):
        return checksum in self._mapping

    def get(self, checksum):
        return self._mapping.get(checksum, [])
        
    def clear(self):
        self._mapping = {}
        
    def __iter__(self):
        for checksum in self._mapping.keys():
            for chunkid in self._mapping[checksum]:
                yield chunkid, checksum


class BackupPlugin(obnamlib.ObnamPlugin):

    def enable(self):
        backup_group = obnamlib.option_group['backup'] = 'Backing up'
        perf_group = obnamlib.option_group['perf']
    
        self.app.add_subcommand('backup', self.backup,
                                arg_synopsis='[DIRECTORY]...')
        self.app.settings.string_list(['root'], 'what to backup')
        self.app.settings.string_list(['exclude'], 
                                 'regular expression for pathnames to '
                                 'exclude from backup (can be used multiple '
                                 'times)',
                                 group=backup_group)
        self.app.settings.boolean(['exclude-caches'],
                                    'exclude directories (and their subdirs) '
                                    'that contain a CACHEDIR.TAG file',
                                 group=backup_group)
        self.app.settings.boolean(['one-file-system'],
                                    'exclude directories (and their subdirs) '
                                    'that are in a different filesystem',
                                 group=backup_group)
        self.app.settings.bytesize(['checkpoint'],
                                      'make a checkpoint after a given SIZE '
                                      '(%default)',
                                    metavar='SIZE',
                                    default=1024**3,
                                 group=backup_group)
        self.app.settings.integer(['chunkids-per-group'],
                                  'encode NUM chunk ids per group (%default)',
                                  metavar='NUM',
                                  default=obnamlib.DEFAULT_CHUNKIDS_PER_GROUP,
                                  group=perf_group)
        self.app.settings.choice(['deduplicate'],
                                 ['fatalist', 'never', 'verify'],
                                 'find duplicate data in backed up data '
                                    'and store it only once; three modes '
                                    'are available: never de-duplicate, '
                                    'verify that no hash collisions happen, '
                                    'or (the default) fatalistically accept '
                                    'the risk of collisions',
                                 metavar='MODE',
                                 group=backup_group)
        self.app.settings.boolean(['leave-checkpoints'],
                                  'leave checkpoint generations at the end '
                                    'of a successful backup run',
                                 group=backup_group)
        self.app.settings.boolean(['small-files-in-btree'],
                                  'put contents of small files directly into '
                                    'the per-client B-tree, instead of '
                                    'separate chunk files; do not use this '
                                    'as it is quite bad for performance',
                                 group=backup_group)

        self.app.settings.string_list(
            ['testing-fail-matching'],
            'development testing helper: simulate failures during backup '
                'for files that match the given regular expressions',
            metavar='REGEXP')

    def configure_ttystatus_for_backup(self):
        self.app.ts['current-file'] = ''
        self.app.ts['uploaded-bytes'] = 0
        self.file_count = 0
        self.backed_up_count = 0
        self.uploaded_bytes = 0

        self.app.ts.format('%ElapsedTime() '
                           '%Counter(current-file) '
                           'files; '
                           '%ByteSize(uploaded-bytes) '
                           '('
                           '%ByteSpeed(uploaded-bytes,10)'
                           ') '
                           '%String(what)')

    def what(self, what_what):
        self.app.ts['what'] = what_what
        self.app.ts.flush()

    def update_progress(self):
        self.app.ts['not-shown'] = 'not shown'

    def configure_ttystatus_for_checkpoint_removal(self):
        self.what('removing checkpoints')

    def update_progress_with_file(self, filename, metadata):
        self.app.ts['what'] = filename
        self.app.ts['current-file'] = filename
        self.file_count += 1

    def update_progress_with_upload(self, amount):
        self.app.ts['uploaded-bytes'] += amount
        self.uploaded_bytes += amount

    def report_stats(self):
        size_table = [
            (1024**4, 'TiB'),
            (1024**3, 'GiB'),
            (1024**2, 'MiB'),
            (1024**1, 'KiB'),
            (0, 'B')
        ]
        
        for size_base, size_unit in size_table:
            if self.uploaded_bytes >= size_base:
                if size_base > 0:
                    size_amount = float(self.uploaded_bytes) / float(size_base)
                else:
                    size_amount = float(self.uploaded_bytes)
                break

        speed_table = [
            (1024**3, 'GiB/s'),
            (1024**2, 'MiB/s'),
            (1024**1, 'KiB/s'),
            (0, 'B/s')
        ]
        duration = time.time() - self.started
        speed = float(self.uploaded_bytes) / duration
        for speed_base, speed_unit in speed_table:
            if speed >= speed_base:
                if speed_base > 0:
                    speed_amount = speed / speed_base
                else:
                    speed_amount = speed
                break

        duration_string = ''
        seconds = duration
        if seconds >= 3600:
            duration_string += '%dh' % int(seconds/3600)
            seconds %= 3600
        if seconds >= 60:
            duration_string += '%dm' % int(seconds/60)
            seconds %= 60
        if seconds > 0:
            duration_string += '%ds' % round(seconds)

        logging.info('Backup performance statistics:')
        logging.info('* files found: %s' % self.file_count)
        logging.info('* files backed up: %s' % self.backed_up_count)
        logging.info('* uploaded data: %s bytes (%s %s)' % 
                        (self.uploaded_bytes, size_amount, size_unit))
        logging.info('* duration: %s s' % duration)
        logging.info('* average speed: %s %s' % (speed_amount, speed_unit))
        self.app.ts.notify(
            'Backed up %d files (of %d found), '
            'uploaded %.1f %s in %s at %.1f %s average speed' %
                (self.backed_up_count, self.file_count,
                 size_amount, size_unit,
                 duration_string, speed_amount, speed_unit))

    def error(self, msg, exc=None):
        self.errors = True
        logging.error(msg)
        if exc:
            logging.error(repr(exc))
            
        # FIXME: ttystatus.TerminalStatus.error is quiet if --quiet is used.
        # That's a bug, so we work around it by writing to stderr directly.
        sys.stderr.write('ERROR: %s\n' % msg)

    def parse_checkpoint_size(self, value):
        p = obnamlib.ByteSizeParser()
        p.set_default_unit('MiB')
        return p.parse(value)
        
    @property
    def pretend(self):
        return self.app.settings['pretend']

    def backup(self, args):
        '''Backup data to repository.'''
        logging.info('Backup starts')
        logging.debug(
            'Checkpoints every %s bytes' % self.app.settings['checkpoint'])

        self.app.settings.require('repository')
        self.app.settings.require('client-name')
        
        if not self.app.settings['repository']:
            raise obnamlib.Error('No --repository setting. '
                                  'You need to specify it on the command '
                                  'line or a configuration file.')
        
        # This is ugly, but avoids having to update the dependency on
        # ttystatus yet again.
        if not hasattr(self.app.ts, 'flush'):
            self.app.ts.flush = lambda: None

        self.started = time.time()
        self.configure_ttystatus_for_backup()
        self.what('setting up')

        self.compile_exclusion_patterns()
        self.memory_dump_counter = 0

        self.what('connecting to repository')
        client_name = self.app.settings['client-name']
        if self.pretend:
            self.repo = self.app.open_repository()
            self.repo.open_client(client_name)
        else:
            self.repo = self.app.open_repository(create=True)
            self.what('adding client')
            self.add_client(client_name)
            self.what('locking client')
            self.repo.lock_client(client_name)
            
            # Need to lock the shared stuff briefly, so encryption etc
            # gets initialized.
            self.what('initialising encryption for shared directories')
            self.repo.lock_shared()
            self.repo.unlock_shared()

        self.errors = False
        self.chunkid_pool = ChunkidPool()
        try:
            if not self.pretend:
                self.what('starting new generation')
                self.repo.start_generation()
            self.fs = None
            roots = self.app.settings['root'] + args
            if not roots:
                raise obnamlib.Error('No backup roots specified')
            self.backup_roots(roots)
            self.what('committing changes to repository')
            if not self.pretend:
                self.what(
                    'committing changes to repository: locking shared B-trees')
                self.repo.lock_shared()
                self.what(
                    'committing changes to repository: '
                    'adding chunks to shared B-trees')
                self.add_chunks_to_shared()
                self.what(
                    'committing changes to repository: '
                    'committing client')
                self.repo.commit_client()
                self.what(
                    'committing changes to repository: '
                    'committing shared B-trees')
                self.repo.commit_shared()
            self.what('closing connection to repository')
            self.repo.fs.close()
            self.app.ts.clear()
            self.report_stats()

            logging.info('Backup finished.')
            self.app.dump_memory_profile('at end of backup run')
        except BaseException, e:
            logging.debug('Handling exception %s' % str(e))
            logging.debug(traceback.format_exc())
            self.unlock_when_error()
            raise

        if self.errors:
            raise obnamlib.Error('There were errors during the backup')

    def unlock_when_error(self):
        try:
            if self.repo.got_client_lock:
                logging.info('Attempting to unlock client because of error')
                self.repo.unlock_client()
            if self.repo.got_shared_lock:
                logging.info(
                    'Attempting to unlock shared trees because of error')
                self.repo.unlock_shared()
        except BaseException, e2:
            logging.error(
                'Error while unlocking due to error: %s' % str(e2))
            logging.debug(traceback.format_exc())
            raise
        else:
            logging.info('Successfully unlocked')

    def add_chunks_to_shared(self):
        for chunkid, checksum in self.chunkid_pool:
            self.repo.put_chunk_in_shared_trees(chunkid, checksum)
        self.chunkid_pool.clear()

    def add_client(self, client_name):
        self.repo.lock_root()
        if client_name not in self.repo.list_clients():
            tracing.trace('adding new client %s' % client_name)
            tracing.trace('client list before adding: %s' % 
                            self.repo.list_clients())
            self.repo.add_client(client_name)
            tracing.trace('client list after adding: %s' % 
                            self.repo.list_clients())
        self.repo.commit_root()
        self.repo = self.app.open_repository(repofs=self.repo.fs.fs)

    def compile_exclusion_patterns(self):
        log = self.app.settings['log']
        if log:
            log = self.app.settings['log']
            self.app.settings['exclude'].append(log)
        for pattern in self.app.settings['exclude']:
            logging.debug('Exclude pattern: %s' % pattern)

        self.exclude_pats = []
        for x in self.app.settings['exclude']:
            try:
                self.exclude_pats.append(re.compile(x))
            except re.error, e:
                msg = 'error compiling regular expression "%s": %s' % (x, e)
                logging.error(msg)
                self.app.ts.error(msg)

    def backup_roots(self, roots):
        self.what('connecting to to repository')
        self.fs = self.app.fsf.new(roots[0])
        self.fs.connect()

        absroots = []
        for root in roots:
            self.what('determining absolute path for %s' % root)
            self.fs.reinit(root)
            absroots.append(self.fs.abspath('.'))
        
        if not self.pretend:
            self.remove_old_roots(absroots)

        self.checkpoints = []
        self.last_checkpoint = 0
        self.interval = self.app.settings['checkpoint']

        for root in roots:
            logging.info('Backing up root %s' % root)
            self.what('connecting to live data %s' % root)
            self.fs.reinit(root)
            
            self.what('scanning for files in %s' % root)
            absroot = self.fs.abspath('.')
            self.root_metadata = self.fs.lstat(absroot)

            for pathname, metadata in self.find_files(absroot):
                logging.info('Backing up %s' % pathname)
                try:
                    self.maybe_simulate_error(pathname)
                    if stat.S_ISDIR(metadata.st_mode):
                        self.backup_dir_contents(pathname)
                    elif stat.S_ISREG(metadata.st_mode):
                        assert metadata.md5 is None
                        metadata.md5 = self.backup_file_contents(pathname,
                                                                 metadata)
                    self.backup_metadata(pathname, metadata)
                except (IOError, OSError), e:
                    msg = 'Can\'t back up %s: %s' % (pathname, e.strerror)
                    self.error(msg, e)
                    if e.errno == errno.ENOSPC:
                        raise
                if self.time_for_checkpoint():
                    self.make_checkpoint()

            self.backup_parents('.')

        remove_checkpoints = (not self.errors and
                              not self.app.settings['leave-checkpoints']
                              and not self.pretend)
        if remove_checkpoints:
            self.configure_ttystatus_for_checkpoint_removal()
            for gen in self.checkpoints:
                self.app.ts['checkpoint'] = gen
                self.repo.remove_generation(gen)

        if self.fs:
            self.fs.close()

    def maybe_simulate_error(self, pathname):
        '''Raise an IOError if specified by --testing-fail-matching.'''
        
        for pattern in self.app.settings['testing-fail-matching']:
            if re.search(pattern, pathname):
                e = errno.ENOENT
                raise IOError(e, os.strerror(e), pathname)

    def time_for_checkpoint(self):
        bytes_since = (self.repo.fs.bytes_written - self.last_checkpoint)
        return bytes_since >= self.interval

    def make_checkpoint(self):
        logging.info('Making checkpoint')
        self.what('making checkpoint')
        if not self.pretend:
            self.checkpoints.append(self.repo.new_generation)
            self.what('making checkpoint: backing up parents')
            self.backup_parents('.')
            self.what('making checkpoint: locking shared B-trees')
            self.repo.lock_shared()
            self.what('making checkpoint: adding chunks to shared B-trees')
            self.add_chunks_to_shared()
            self.what('making checkpoint: committing per-client B-tree')
            self.repo.commit_client(checkpoint=True)
            self.what('making checkpoint: committing shared B-trees')
            self.repo.commit_shared()
            self.last_checkpoint = self.repo.fs.bytes_written
            self.what('making checkpoint: re-opening repository')
            self.repo = self.app.open_repository(repofs=self.repo.fs.fs)
            self.what('making checkpoint: locking client')
            self.repo.lock_client(self.app.settings['client-name'])
            self.what('making checkpoint: starting a new generation')
            self.repo.start_generation()
            self.app.dump_memory_profile('at end of checkpoint')
            self.what('making checkpoint: continuing backup')
        self.what(self.app.ts['current-file'])

    def find_files(self, root):
        '''Find all files and directories that need to be backed up.
        
        This is a generator. It yields (pathname, metadata) pairs.
        
        The caller should not recurse through directories, just backup
        the directory itself (name, metadata, file list).
        
        '''

        for pathname, st in self.fs.scan_tree(root, ok=self.can_be_backed_up):
            tracing.trace('considering %s' % pathname)
            try:
                metadata = obnamlib.read_metadata(self.fs, pathname, st=st)
                self.update_progress_with_file(pathname, metadata)
                if self.needs_backup(pathname, metadata):
                    self.backed_up_count += 1
                    yield pathname, metadata
            except GeneratorExit:
                raise
            except KeyboardInterrupt:
                logging.error('Keyboard interrupt')
                raise
            except BaseException, e:
                msg = 'Cannot back up %s: %s' % (pathname, str(e))
                self.error(msg, e)

    def can_be_backed_up(self, pathname, st):
        if self.app.settings['one-file-system']:
            if st.st_dev != self.root_metadata.st_dev: 
                logging.debug('Excluding (one-file-system): %s' % pathname)
                return False

        for pat in self.exclude_pats:
            if pat.search(pathname):
                logging.debug('Excluding (pattern): %s' % pathname)
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
                    logging.debug('Excluding (cache dir): %s' % pathname)
                    return False
        
        return True

    def needs_backup(self, pathname, current):
        '''Does a given file need to be backed up?'''
        
        # Directories always require backing up so that backup_dir_contents
        # can remove stuff that no longer exists from them.
        if current.isdir():
            tracing.trace('%s is directory, so needs backup' % pathname)
            return True
        if self.pretend:
            gens = self.repo.list_generations()
            if not gens:
                return True
            gen = gens[-1]
        else:
            gen = self.repo.new_generation
        tracing.trace('gen=%s' % repr(gen))
        try:
            old = self.repo.get_metadata(gen, pathname)
        except obnamlib.Error, e:
            # File does not exist in the previous generation, so it
            # does need to be backed up.
            tracing.trace('%s not in previous gen, so needs backup' % pathname)
            tracing.trace('error: %s' % str(e))
            tracing.trace(traceback.format_exc())
            return True

        needs = (current.st_mtime_sec != old.st_mtime_sec or
                 current.st_mtime_nsec != old.st_mtime_nsec or
                 current.st_mode != old.st_mode or
                 current.st_nlink != old.st_nlink or
                 current.st_size != old.st_size or
                 current.st_uid != old.st_uid or
                 current.st_gid != old.st_gid or
                 current.xattr != old.xattr)
        if needs:
            tracing.trace('%s has changed metadata, so needs backup' % pathname)
        return needs

    def backup_parents(self, root):
        '''Back up parents of root, non-recursively.'''
        root = self.fs.abspath(root)
        tracing.trace('backing up parents of %s', root)

        dummy_metadata = obnamlib.Metadata(st_mode=0777 | stat.S_IFDIR)

        while True:
            parent = os.path.dirname(root)
            try:
                metadata = obnamlib.read_metadata(self.fs, root)
            except OSError, e:
                logging.warning(
                    'Failed to get metadata for %s: %s: %s' %
                        (root, e.errno or 0, e.strerror))
                logging.warning('Using fake metadata instead for %s' % root)
                metadata = dummy_metadata
            if not self.pretend:
                self.repo.create(root, metadata)
            if root == parent:
                break
            root = parent

    def backup_metadata(self, pathname, metadata):
        '''Back up metadata for a filesystem object'''
        
        tracing.trace('backup_metadata: %s', pathname)
        if not self.pretend:
            self.repo.create(pathname, metadata)

    def backup_file_contents(self, filename, metadata):
        '''Back up contents of a regular file.'''
        tracing.trace('backup_file_contents: %s', filename)
        if self.pretend:
            tracing.trace('pretending to upload the whole file')
            self.update_progress_with_upload(metadata.st_size)
            return

        tracing.trace('setting file chunks to empty')
        if not self.pretend:
            self.repo.set_file_chunks(filename, [])

        tracing.trace('opening file for reading')
        f = self.fs.open(filename, 'r')

        summer = self.repo.new_checksummer()

        max_intree = self.app.settings['node-size'] / 4
        if (metadata.st_size <= max_intree and 
            self.app.settings['small-files-in-btree']):
            contents = f.read()
            assert len(contents) <= max_intree # FIXME: silly error checking
            f.close()
            self.repo.set_file_data(filename, contents)
            summer.update(contents)
            return summer.digest()

        chunk_size = int(self.app.settings['chunk-size'])
        chunkids = []
        while True:
            tracing.trace('reading some data')
            self.update_progress()
            data = f.read(chunk_size)
            if not data:
                tracing.trace('end of data')
                break
            tracing.trace('got %d bytes of data' % len(data))
            summer.update(data)
            if not self.pretend:
                chunkids.append(self.backup_file_chunk(data))
                if len(chunkids) >= self.app.settings['chunkids-per-group']:
                    tracing.trace('adding %d chunkids to file' % len(chunkids))
                    self.repo.append_file_chunks(filename, chunkids)
                    self.app.dump_memory_profile('after appending some '
                                                    'chunkids')
                    chunkids = []
            else:
                self.update_progress_with_upload(len(data))
            
            if not self.pretend and self.time_for_checkpoint():
                logging.debug('making checkpoint in the middle of a file')
                self.repo.append_file_chunks(filename, chunkids)
                chunkids = []
                self.make_checkpoint()
            
        tracing.trace('closing file')
        f.close()
        if chunkids:
            assert not self.pretend
            tracing.trace('adding final %d chunkids to file' % len(chunkids))
            self.repo.append_file_chunks(filename, chunkids)
        self.app.dump_memory_profile('at end of file content backup for %s' %
                                     filename)
        tracing.trace('done backing up file contents')
        return summer.digest()
        
    def backup_file_chunk(self, data):
        '''Back up a chunk of data by putting it into the repository.'''

        def find():
            # We ignore lookup errors here intentionally. We're reading
            # the checksum trees without a lock, so another Obnam may be
            # modifying them, which can lead to spurious NodeMissing
            # exceptions, and other errors. We don't care: we'll just
            # pretend no chunk with the checksum exists yet.
            try:
                in_tree = self.repo.find_chunks(checksum)
            except larch.Error:
                in_tree = []
            return in_tree + self.chunkid_pool.get(checksum)

        def get(chunkid):
            return self.repo.get_chunk(chunkid)

        def put():
            self.update_progress_with_upload(len(data))
            return self.repo.put_chunk_only(data)
            
        def share(chunkid):
            self.chunkid_pool.add(chunkid, checksum)

        checksum = self.repo.checksum(data)

        mode = self.app.settings['deduplicate']
        if mode == 'never':
            return put()
        elif mode == 'verify':
            for chunkid in find():
                data2 = get(chunkid)
                if data == data2:
                    return chunkid
            else:
                chunkid = put()
                share(chunkid)
                return chunkid
        elif mode == 'fatalist':
            existing = find()
            if existing:
                return existing[0]
            else:
                chunkid = put()
                share(chunkid)
                return chunkid
        else:
            if not hasattr(self, 'bad_deduplicate_reported'):
                logging.error('unknown --deduplicate setting value')
                self.bad_deduplicate_reported = True
            chunkid = put()
            share(chunkid)
            return chunkid

    def backup_dir_contents(self, root):
        '''Back up the list of files in a directory.'''

        tracing.trace('backup_dir: %s', root)
        if self.pretend:
            return

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
            if not pathname.endswith(os.sep):
                pathname += os.sep
            for new_root in new_roots:
                if new_root.startswith(pathname):
                    return True
            return False
            
        def helper(dirname):
            if dirname in new_roots:
                tracing.trace('is a new root: %s' % dirname)
            elif is_parent(dirname):
                tracing.trace('is parent of a new root: %s' % dirname)
                pathnames = [os.path.join(dirname, x)
                             for x in self.repo.listdir(gen_id, dirname)]
                for pathname in pathnames:
                    helper(pathname)
            else:
                tracing.trace('is extra and removed: %s' % dirname)
                self.what('removing %s from new generation' % dirname)
                self.repo.remove(dirname)
                self.what(msg)

        assert not self.pretend
        msg = 'removing old backup roots from new generation'
        self.what(msg)
        tracing.trace('new_roots: %s' % repr(new_roots))
        gen_id = self.repo.new_generation
        helper('/')

