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


import hashlib
import larch.fsck
import logging
import os
import stat
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
        if not self.repo.has_chunk(self.chunkid):
            self.error('chunk %s does not exist' % self.chunkid)
        else:
            data = self.repo.get_chunk_content(self.chunkid)
            self.checksummer.update(data)

            valid = self.repo.validate_chunk_content(self.chunkid)
            if valid is False:
                self.error('chunk %s is corrupted' % self.chunkid)

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
        self.name = 'file %s:%s:%s' % (client_name, genid, filename)

    def do(self):
        logging.debug('Checking client=%s genid=%s filename=%s' %
                        (self.client_name, self.genid, self.filename))
        mode = self.repo.get_file_key(
            self.genid, self.filename, obnamlib.REPO_FILE_MODE)
        if stat.S_ISREG(mode) and not self.settings['fsck-ignore-chunks']:
            chunkids = self.repo.get_file_chunk_ids(self.genid, self.filename)
            checksummer = hashlib.md5()
            for chunkid in chunkids:
                yield CheckChunk(chunkid, checksummer)
            md5 = self.repo.get_file_key(
                self.genid, self.filename, obnamlib.REPO_FILE_MD5)
            yield CheckFileChecksum(
                self.name, md5, chunkids, checksummer)


class CheckDirectory(WorkItem):

    def __init__(self, client_name, genid, dirname):
        self.client_name = client_name
        self.genid = genid
        self.dirname = dirname
        self.name = 'dir %s:%s:%s' % (client_name, genid, dirname)

    def do(self):
        logging.debug('Checking client=%s genid=%s dirname=%s' %
                        (self.client_name, self.genid, self.dirname))
        for pathname in self.repo.get_file_children(self.genid, self.dirname):
            mode = self.repo.get_file_key(
                self.genid, pathname, obnamlib.REPO_FILE_MODE)
            if stat.S_ISDIR(mode):
                yield CheckDirectory(self.client_name, self.genid, pathname)
            elif not self.settings['fsck-skip-files']:
                yield CheckFile(self.client_name, self.genid, pathname)


class CheckGeneration(WorkItem):

    def __init__(self, client_name, genid):
        self.client_name = client_name
        self.genid = genid
        self.name = 'generation %s:%s' % (client_name, genid)

    def do(self):
        logging.debug('Checking client=%s genid=%s' %
                        (self.client_name, self.genid))

        started = self.repo.get_generation_key(
            self.genid, obnamlib.REPO_GENERATION_STARTED)
        ended = self.repo.get_generation_key(
            self.genid, obnamlib.REPO_GENERATION_ENDED)
        if started is None:
            self.error('%s:%s: no generation start time' %
                        (self.client_name, self.genid))
        if ended is None:
            self.error('%s:%s: no generation end time' %
                        (self.client_name, self.genid))

        n = self.repo.get_generation_key(
            self.genid, obnamlib.REPO_GENERATION_FILE_COUNT)
        if n is None:
            self.error('%s:%s: no file count' % (self.client_name, self.genid))

        n = self.repo.get_generation_key(
            self.genid, obnamlib.REPO_GENERATION_TOTAL_DATA)
        if n is None:
            self.error('%s:%s: no total data' % (self.client_name, self.genid))

        if self.settings['fsck-skip-dirs']:
            return []
        else:
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


class CheckClient(WorkItem):

    def __init__(self, client_name):
        self.client_name = client_name
        self.name = 'client %s' % client_name

    def do(self):
        logging.debug('Checking client=%s' % self.client_name)
        genids = self.repo.get_client_generation_ids(self.client_name)
        yield CheckGenerationIdsAreDifferent(self.client_name, genids)
        if self.settings['fsck-skip-generations']:
            genids = []
        elif self.settings['fsck-last-generation-only'] and genids:
            genids = genids[-1:]
        for genid in genids:
            yield CheckGeneration(self.client_name, genid)


class CheckClientlist(WorkItem):

    name = 'client list'

    def do(self):
        logging.debug('Checking clientlist')
        clients = self.repo.get_client_names()
        if not self.settings['fsck-skip-per-client-b-trees']:
            for client_name in clients:
                if client_name not in self.settings['fsck-ignore-client']:
                    # FIXME: This can't be done using the public API of
                    # RepositoryInterface. The API needs improvement.
                    client_id = self.repo._client_list.get_client_id(
                        client_name)
                    client_dir = self.repo._get_client_dir(client_id)
                    yield CheckBTree(str(client_dir))
        for client_name in clients:
            if client_name not in self.settings['fsck-ignore-client']:
                yield CheckClient(client_name)


class CheckForExtraChunks(WorkItem):

    def __init__(self):
        self.name = 'extra chunks'

    def do(self):
        logging.debug('Checking for extra chunks')
        # FIXME: This can't be done using the RepositoryInterface API.
        # It is disabled, for now.
        # for chunkid in self.repo.list_chunks():
        #     if chunkid not in self.chunkids_seen:
        #         self.error('chunk %s not used by anyone' % chunkid)


class CheckBTree(WorkItem):

    def __init__(self, dirname):
        self.dirname = dirname
        self.name = 'B-tree %s' % dirname

    def do(self):
        if not self.repo.get_fs().exists(self.dirname):
            logging.debug('B-tree %s does not exist, skipping' % self.dirname)
            return
        logging.debug('Checking B-tree %s' % self.dirname)
        fix = self.settings['fsck-fix']
        # FIXME: The RepositoryInterface API does not have a way to expose
        # the "hooked" filesystem, which is necessary for accessing
        # the repository using encryption or compression or such. We
        # kluge this for now.
        forest = larch.open_forest(allow_writes=fix, dirname=self.dirname,
                                   vfs=self.repo._fs)
        fsck = larch.fsck.Fsck(forest, self.warning, self.error, fix)
        for work in fsck.find_work():
            yield work


class CheckRepository(WorkItem):

    def __init__(self):
        self.name = 'repository'

    def do(self):
        logging.debug('Checking repository')
        if not self.settings['fsck-skip-shared-b-trees']:
            yield CheckBTree('clientlist')
            yield CheckBTree('chunklist')
            yield CheckBTree('chunksums')
        yield CheckClientlist()
        for work in self.repo.get_fsck_work_item():
            yield work


class FsckPlugin(obnamlib.ObnamPlugin):

    def enable(self):
        self.app.add_subcommand('fsck', self.fsck)

        group = 'Integrity checking (fsck)'

        self.app.settings.boolean(
            ['fsck-fix'],
            'should fsck try to fix problems?',
            group=group)

        self.app.settings.boolean(
            ['fsck-ignore-chunks'],
            'ignore chunks when checking repository integrity (assume all '
                'chunks exist and are correct)',
            group=group)

        self.app.settings.string_list(
            ['fsck-ignore-client'],
            'do not check repository data for cient NAME',
            metavar='NAME',
            group=group)

        self.app.settings.boolean(
            ['fsck-last-generation-only'],
            'check only the last generation for each client',
            group=group)

        self.app.settings.boolean(
            ['fsck-skip-generations'],
            'do not check any generations',
            group=group)

        self.app.settings.boolean(
            ['fsck-skip-dirs'],
            'do not check anything about directories and their files',
            group=group)

        self.app.settings.boolean(
            ['fsck-skip-files'],
            'do not check anything about files',
            group=group)

        self.app.settings.boolean(
            ['fsck-skip-per-client-b-trees'],
            'do not check per-client B-trees',
            group=group)

        self.app.settings.boolean(
            ['fsck-skip-shared-b-trees'],
            'do not check shared B-trees',
            group=group)

    def configure_ttystatus(self):
        self.app.ts.clear()
        self.app.ts['this_item'] = 0
        self.app.ts['items'] = 0
        self.app.ts.format(
            'Checking %Integer(this_item)/%Integer(items): %String(item)')

    def fsck(self, args):
        '''Verify internal consistency of backup repository.'''
        self.app.settings.require('repository')
        logging.debug('fsck on %s' % self.app.settings['repository'])

        self.configure_ttystatus()

        self.repo = self.app.get_repository_object()

        self.repo.lock_client_list()
        client_names = self.repo.get_client_names()
        for client_name in client_names:
            self.repo.lock_client(client_name)
        self.repo.lock_chunk_indexes()

        self.errors = 0
        self.chunkids_seen = set()
        self.work_items = []
        self.add_item(CheckRepository(), append=True)

        final_items = []
        if not self.app.settings['fsck-ignore-chunks']:
            final_items.append(CheckForExtraChunks())

        while self.work_items:
            work = self.work_items.pop(0)
            logging.debug('doing: %s' % str(work))
            self.app.ts['item'] = work
            self.app.ts.increase('this_item', 1)
            pos = 0
            for more in work.do() or []:
                self.add_item(more, pos=pos)
                pos += 1
            if not self.work_items:
                for work in final_items:
                    self.add_item(work, append=True)
                final_items = []

        self.repo.unlock_chunk_indexes()
        for client_name in client_names:
            self.repo.unlock_client(client_name)
        self.repo.unlock_client_list()

        self.repo.close()
        self.app.ts.finish()

        if self.errors:
            sys.exit(1)

    def add_item(self, work, append=False, pos=0):
        logging.debug('adding: %s' % str(work))
        work.warning = self.warning
        work.error = self.error
        work.repo = self.repo
        work.settings = self.app.settings
        work.chunkids_seen = self.chunkids_seen
        if append:
            self.work_items.append(work)
        else:
            self.work_items.insert(pos, work)
        self.app.ts.increase('items', 1)

    def error(self, msg):
        logging.error(msg)
        self.app.ts.error(msg)
        self.errors += 1

    def warning(self, msg):
        logging.warning(msg)
        self.app.ts.notify(msg)

