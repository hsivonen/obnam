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
import sys
import ttystatus

import obnamlib


class WorkItem(object):

    '''A work item for fsck.
    
    Subclass must define a ``name`` attribute, and override the ``do``
    method to do the actual work. Whoever creates a WorkItem shall
    set the ``ts`` attribute to be a ``ttystatus.TerminalStatus``
    instance, and ``repo`` to the repository being used.
    
    '''

    def __str__(self):
        if hasattr(self, 'name'):
            return self.name
        else:
            return self.__class__.__name__

    def do(self):
        pass


class CheckChunk(WorkItem):

    def __init__(self, chunkid, checksummer):
        self.chunkid = chunkid
        self.checksummer = checksummer
        self.name = 'chunk %s' % chunkid

    def do(self):
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
        self.name = '%s checksum' % filename
        self.correct = correct
        self.chunkids = chunkids
        self.checksummer = checksummer
        
    def do(self):
        if self.correct != self.checksummer.digest():
            self.error('%s whole-file checksum mismatch' % self.name)


class CheckFile(WorkItem):

    def __init__(self, client_name, genid, filename):
        self.client_name = client_name
        self.genid = genid
        self.filename = filename
        self.name = '%s:%s:%s' % (client_name, genid, filename)

    def do(self):
        self.repo.open_client(self.client_name)
        metadata = self.repo.get_metadata(self.genid, self.filename)
        if metadata.isfile():
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
        self.name = '%s:%s' % (client_name, genid)
        
    def do(self):
        started, ended = self.repo.client.get_generation_times(self.genid)
        if started is None:
            self.error('%s:%s: no generation start time' %
                        (self.client_name, self.genid))
        if ended is None:
            self.error('%s:%s: no generation end time' %
                        (self.client_name, self.genid))

        n = self.repo.client.get_generation_files(self.genid)
        if n is None:
            self.error('%s:%s: no file count' % (self.client_name, self.genid))

        n = self.repo.client.get_generation_data(self.genid)
        if n is None:
            self.error('%s:%s: no total data' % (self.client_name, self.genid))

        return [CheckDirectory(self.client_name, self.genid, '/')]


class CheckClientExists(WorkItem):

    def __init__(self, client_name):
        self.client_name = client_name
        self.name = 'does client %s exist?' % client_name

    def do(self):
        client_id = self.repo.clientlist.get_client_id(self.client_name)
        if client_id is None:
            self.error('Client %s is in client list, but has no id' %
                          self.client_name)


class CheckClient(WorkItem):

    def __init__(self, client_name):
        self.client_name = client_name
        self.name = 'client %s' % client_name

    def do(self):
        self.repo.open_client(self.client_name)
        for genid in self.repo.list_generations():
            yield CheckGeneration(self.client_name, genid)


class CheckClientlist(WorkItem):

    name = 'client list'

    def do(self):
        for client_name in self.repo.clientlist.list_clients():
            yield CheckClientExists(client_name)
        for client_name in self.repo.clientlist.list_clients():
            yield CheckClient(client_name)


class CheckForExtraChunks(WorkItem):

    def __init__(self):
        self.name = 'extra chunks'
        
    def do(self):
        for chunkid in self.repo.list_chunks():
            if chunkid not in self.chunkids_seen:
                self.error('chunk %s not used by anyone' % chunkid)


class CheckRepository(WorkItem):

    def __init__(self):
        self.name = 'repository'
        
    def do(self):
        yield CheckClientlist()


class FsckPlugin(obnamlib.ObnamPlugin):

    def enable(self):
        self.app.add_subcommand('fsck', self.fsck)

    def configure_ttystatus(self, work_items):
        self.app.ts.clear()
        self.app.ts['item'] = None
        self.app.ts['items'] = work_items
        self.app.ts.format('Checking %Index(item,items): %String(item)')
        
    def fsck(self, args):
        '''Verify internal consistency of backup repository.'''
        self.app.settings.require('repository')
        logging.debug('fsck on %s' % self.app.settings['repository'])
        self.repo = self.app.open_repository()

        self.errors = 0
        self.chunkids_seen = set()
        self.work_items = []
        self.add_item(CheckRepository())
        final_items = [CheckForExtraChunks()]
        
        self.configure_ttystatus(self.work_items)
        i = 0
        while i < len(self.work_items):
            work = self.work_items[i]
            logging.debug('doing: %s' % str(work))
            self.app.ts['item'] = work
            for more in work.do() or []:
                self.add_item(more)
            i += 1
            if i == len(self.work_items):
                for work in final_items:
                    self.add_item(work)
                final_items = []

        self.repo.fs.close()
        self.app.ts.finish()
        
        if self.errors:
            sys.exit(1)

    def add_item(self, work):
        work.error = self.error
        work.repo = self.repo
        work.chunkids_seen = self.chunkids_seen
        self.work_items.append(work)

    def error(self, msg):
        self.app.ts.error(msg)
        self.errors += 1

