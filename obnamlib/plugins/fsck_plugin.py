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


class CheckClientExists(WorkItem):

    def __init__(self, client_name):
        self.client_name = client_name
        self.name = 'does client %s exist?' % client_name

    def do(self):
        client_id = self.repo.clientlist.get_client_id(self.client_name)
        if client_id is None:
            self.ts.error('Client %s is in client list, but has no id' %
                          self.client_name)


class CheckClient(WorkItem):

    def __init__(self, client_name):
        self.client_name = client_name
        self.name = 'client %s' % client_name

    def do(self):
        self.repo.open_client(self.client_name)
        for genid in self.repo.list_generations():
            pass
#            yield CheckGeneration(self.client_name, genid)


class CheckClientlist(WorkItem):

    name = 'client list'

    def do(self):
        for client_name in self.repo.clientlist.list_clients():
            yield CheckClientExists(client_name)
        for client_name in self.repo.clientlist.list_clients():
            yield CheckClient(client_name)


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

        self.work_items = []
        self.add_item(CheckClientlist())
        self.configure_ttystatus(self.work_items)
        i = 0
        while i < len(self.work_items):
            work = self.work_items[i]
            self.app.ts['item'] = work
            for more in work.do() or []:
                self.add_item(more)
            i += 1

        self.repo.fs.close()
        self.app.ts.finish()

    def add_item(self, work):
        work.ts = self.app.ts
        work.repo = self.repo
        self.work_items.append(work)

    def find_work(self):
        work_items = []
        queue = [CheckClientlist()]
        while queue:
            work = queue.pop(0)
            self.app.ts['work'] = str(work)
            work.ts = self.app.ts
            work.repo = self.repo
            work_items.append(work)
            queue.extend(list(work.scan()))
        return work_items

#    def check_client(self, client_name):
#        '''Check a client.'''
#        logging.debug('Checking client %s' % client_name)
#        self.app.ts['what'] = 'Checking client %s' % client_name

#    def check_generation(self, genid):
#        '''Check a generation.'''
#        logging.debug('Checking generation %s' % genid)
#        self.app.ts['what'] = 'Checking generation %s' % genid
#        self.check_dir(genid, '/')

#    def check_dir(self, genid, dirname):
#        '''Check a directory.'''
#        logging.debug('Checking directory %s' % dirname)
#        self.app.ts['what'] = 'Checking dir %s' % dirname
#        self.repo.get_metadata(genid, dirname)
#        for basename in self.repo.listdir(genid, dirname):
#            pathname = os.path.join(dirname, basename)
#            metadata = self.repo.get_metadata(genid, pathname)
#            if metadata.isdir():
#                self.check_dir(genid, pathname)
#            else:
#                self.check_file(genid, pathname)
#                
#    def check_file(self, genid, filename):
#        '''Check a non-directory.'''
#        logging.debug('Checking file %s' % filename)
#        self.app.ts['what'] = 'Checking file %s' % filename
#        metadata = self.repo.get_metadata(genid, filename)
#        if metadata.isfile():
#            for chunkid in self.repo.get_file_chunks(genid, filename):
#                self.check_chunk(chunkid)

#    def check_chunk(self, chunkid):
#        '''Check a chunk.'''
#        logging.debug('Checking chunk %s' % chunkid)
#        self.repo.chunk_exists(chunkid)

