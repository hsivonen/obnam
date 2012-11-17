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


import larch.fsck
import logging
import os
import sys
import ttystatus

import obnamlib


class WorkItem(larch.fsck.WorkItem):

    '''A work item for fsck.
    
    Whoever creates a WorkItem shall set the ``repo`` to the repository 
    being used.
    
    '''


class CheckChunk(WorkItem):

    def __init__(self, chunkid, checksummer):
        self.chunkid = chunkid
        self.checksummer = checksummer
        self.name = 'chunk %s' % chunkid

    def do(self):
        logging.debug('Checking chunk %s' % self.chunkid)
        if not self.repo.chunk_exists(self.chunkid):
            self.error('chunk %s does not exist' % self.chunkid)
        else:
            data = self.repo.get_chunk(self.chunkid)
            checksum = self.repo.checksum(data)
            try:
                correct = self.repo.chunklist.get_checksum(self.chunkid)
            except KeyError:
                self.error('chunk %s not in chunklist' % self.chunkid)
            else:
                if checksum != correct:
                    self.error('chunk %s has wrong checksum' % self.chunkid)

            if self.chunkid not in self.repo.chunksums.find(checksum):
                self.error('chunk %s not in chunksums' % self.chunkid)

            self.checksummer.update(data)
        self.chunkids_seen.add(self.chunkid)


class CheckFileChecksum(WorkItem):

    def __init__(self, filename, correct, chunkids, checksummer):
        self.filename = filename
        self.name = '%s checksum' % filename
        self.correct = correct
        self.chunkids = chunkids
        self.checksummer = checksummer
        
    def do(self):
        logging.debug('Checking whole-file checksum for %s' % self.filename)
        if self.correct != self.checksummer.digest():
            self.error('%s whole-file checksum mismatch' % self.name)


class CheckFile(WorkItem):

    def __init__(self, client_name, genid, filename):
        self.client_name = client_name
        self.genid = genid
        self.filename = filename
        self.name = '%s:%s:%s' % (client_name, genid, filename)

    def do(self):
        logging.debug('Checking client=%s genid=%s filename=%s' %
                        (self.client_name, self.genid, self.filename))
        if self.repo.current_client != self.client_name:
            self.repo.open_client(self.client_name)
        metadata = self.repo.get_metadata(self.genid, self.filename)
        if metadata.isfile() and not self.settings['fsck-ignore-chunks']:
            chunkids = self.repo.get_file_chunks(self.genid, self.filename)
            checksummer = self.repo.new_checksummer()
            for chunkid in chunkids:
                yield CheckChunk(chunkid, checksummer)
            yield CheckFileChecksum(self.name, metadata.md5, chunkids,
                                     checksummer)


class CheckDirectory(WorkItem):

    def __init__(self, client_name, genid, dirname):
        self.client_name = client_name
        self.genid = genid
        self.dirname = dirname
        self.name = '%s:%s:%s' % (client_name, genid, dirname)
        
    def do(self):
        logging.debug('Checking client=%s genid=%s dirname=%s' %
                        (self.client_name, self.genid, self.dirname))
        if self.repo.current_client != self.client_name:
            self.repo.open_client(self.client_name)
        self.repo.get_metadata(self.genid, self.dirname)
        for basename in self.repo.listdir(self.genid, self.dirname):
            pathname = os.path.join(self.dirname, basename)
            metadata = self.repo.get_metadata(self.genid, pathname)
            if metadata.isdir():
                yield CheckDirectory(self.client_name, self.genid, pathname)
            else:
                yield CheckFile(self.client_name, self.genid, pathname)


class CheckGeneration(WorkItem):

    def __init__(self, client_name, genid):
        self.client_name = client_name
        self.genid = genid
        self.name = 'generation %s:%s' % (client_name, genid)
        
    def do(self):
        logging.debug('Checking client=%s genid=%s' % 
                        (self.client_name, self.genid))

        started, ended = self.repo.client.get_generation_times(self.genid)
        if started is None:
            self.error('%s:%s: no generation start time' %
                        (self.client_name, self.genid))
        if ended is None:
            self.error('%s:%s: no generation end time' %
                        (self.client_name, self.genid))

        n = self.repo.client.get_generation_file_count(self.genid)
        if n is None:
            self.error('%s:%s: no file count' % (self.client_name, self.genid))

        n = self.repo.client.get_generation_data(self.genid)
        if n is None:
            self.error('%s:%s: no total data' % (self.client_name, self.genid))

        return [CheckDirectory(self.client_name, self.genid, '/')]


class CheckGenerationIdsAreDifferent(WorkItem):

    def __init__(self, client_name, genids):
        self.client_name = client_name
        self.genids = list(genids)
    
    def do(self):
        logging.debug('Checking genid uniqueness for client=%s' % 
                        self.client_name)
        done = set()
        while self.genids:
            genid = self.genids.pop()
            if genid in done:
                self.error('%s: duplicate generation id %s' % genid)
            else:
                done.add(genid)


class CheckClientExists(WorkItem):

    def __init__(self, client_name):
        self.client_name = client_name
        self.name = 'does client %s exist?' % client_name

    def do(self):
        logging.debug('Checking client=%s exists' % self.client_name)
        client_id = self.repo.clientlist.get_client_id(self.client_name)
        if client_id is None:
            self.error('Client %s is in client list, but has no id' %
                          self.client_name)


class CheckClient(WorkItem):

    def __init__(self, client_name):
        self.client_name = client_name
        self.name = 'client %s' % client_name

    def do(self):
        logging.debug('Checking client=%s' % self.client_name)
        if self.repo.current_client != self.client_name:
            self.repo.open_client(self.client_name)
        genids = self.repo.list_generations()
        yield CheckGenerationIdsAreDifferent(self.client_name, genids)
        for genid in genids:
            yield CheckGeneration(self.client_name, genid)


class CheckClientlist(WorkItem):

    name = 'client list'

    def do(self):
        logging.debug('Checking clientlist')
        clients = self.repo.clientlist.list_clients()
        if not self.settings['fsck-skip-b-trees']:
            for client_name in clients:
                client_id = self.repo.clientlist.get_client_id(client_name)
                client_dir = self.repo.client_dir(client_id)
                yield CheckBTree(str(client_dir))
        for client_name in clients:
            if client_name not in self.settings['fsck-ignore-client']:
                yield CheckClientExists(client_name)
        for client_name in clients:
            if client_name not in self.settings['fsck-ignore-client']:
                yield CheckClient(client_name)


class CheckForExtraChunks(WorkItem):

    def __init__(self):
        self.name = 'extra chunks'
        
    def do(self):
        logging.debug('Checking for extra chunks')
        for chunkid in self.repo.list_chunks():
            if chunkid not in self.chunkids_seen:
                self.error('chunk %s not used by anyone' % chunkid)


class CheckBTree(WorkItem):

    def __init__(self, dirname):
        self.dirname = dirname
        self.name = 'B-tree %s' % dirname

    def do(self):
        if not self.repo.fs.exists(self.dirname):
            logging.debug('B-tree %s does not exist, skipping' % self.dirname)
            return
        logging.debug('Checking B-tree %s' % self.dirname)
        forest = larch.open_forest(allow_writes=False, dirname=self.dirname, 
                                   vfs=self.repo.fs)
        fsck = larch.fsck.Fsck(forest, self.warning, self.error, 
                               self.settings['fsck-fix'])
        for work in fsck.find_work():
            yield work


class CheckRepository(WorkItem):

    def __init__(self):
        self.name = 'repository'
        
    def do(self):
        logging.debug('Checking repository')
        if not self.settings['fsck-skip-b-trees']:
            yield CheckBTree('clientlist')
            yield CheckBTree('chunklist')
            yield CheckBTree('chunksums')
        yield CheckClientlist()


class FsckPlugin(obnamlib.ObnamPlugin):

    def enable(self):
        self.app.add_subcommand('fsck', self.fsck)
        self.app.settings.boolean(['fsck-fix'], 
                                  'should fsck try to fix problems?')
        self.app.settings.boolean(
            ['fsck-ignore-chunks'],
            'ignore chunks when checking repository integrity (assume all '
                'chunks exist and are correct)')
        self.app.settings.boolean(
            ['fsck-skip-b-trees'],
            'skip B-tree integrity checking')
        self.app.settings.string_list(
            ['fsck-ignore-client'],
            'do not check repository data for cient NAME',
            metavar='NAME')

    def configure_ttystatus(self):
        self.app.ts.clear()
        self.app.ts['item'] = None
        self.app.ts['items'] = 0
        self.app.ts.format(
            'Checking %Counter(item)/%Integer(items): %String(item)')
        
    def fsck(self, args):
        '''Verify internal consistency of backup repository.'''
        self.app.settings.require('repository')
        logging.debug('fsck on %s' % self.app.settings['repository'])
        self.repo = self.app.open_repository()
        
        self.repo.lock_root()
        client_names = self.repo.list_clients()
        client_dirs = [self.repo.client_dir(
                            self.repo.clientlist.get_client_id(name))
                       for name in client_names]
        self.repo.lockmgr.lock(client_dirs)
        self.repo.lock_shared()

        self.errors = 0
        self.chunkids_seen = set()
        self.work_items = []
        self.add_item(CheckRepository())

        final_items = []
        if not self.app.settings['fsck-ignore-chunks']:
            final_items.append(CheckForExtraChunks())
        
        self.configure_ttystatus()
        i = 0
        while self.work_items:
            work = self.work_items.pop()
            logging.debug('doing: %s' % str(work))
            self.app.ts['item'] = work
            self.app.ts.flush()
            pos = len(self.work_items)
            for more in work.do() or []:
                self.add_item(more, pos=pos)
            i += 1
            if not self.work_items:
                for work in final_items:
                    self.add_item(work)
                final_items = []

        self.repo.unlock_shared()
        self.repo.lockmgr.unlock(client_dirs)
        self.repo.unlock_root()

        self.repo.fs.close()
        self.app.ts.finish()
        
        if self.errors:
            sys.exit(1)

    def add_item(self, work, append=False, pos=0):
        work.warning = self.warning
        work.error = self.error
        work.repo = self.repo
        work.settings = self.app.settings
        work.chunkids_seen = self.chunkids_seen
        if append:
            self.work_items.append(work)
        else:
            self.work_items.insert(0, work)
        self.app.ts.increase('items', 1)
        self.app.ts.flush()

    def error(self, msg):
        self.app.ts.error(msg)
        self.errors += 1

    def warning(self, msg):
        self.app.ts.notify(msg)

