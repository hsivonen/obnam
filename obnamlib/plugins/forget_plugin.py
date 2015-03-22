# Copyright (C) 2010-2015  Lars Wirzenius
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


import datetime

import obnamlib


class ForgetPlugin(obnamlib.ObnamPlugin):

    '''Forget generations.'''

    def enable(self):
        self.app.add_subcommand('forget', self.forget,
            arg_synopsis='[GENERATION]...')
        self.app.settings.string(
            ['keep'],
            'policy for what generations to keep '
            'when forgetting')

    def forget(self, args):
        '''Forget (remove) specified backup generations.'''
        self.app.settings.require('repository')
        self.app.settings.require('client-name')

        self.app.ts['gen'] = None
        self.app.ts['gens'] = []
        self.app.ts.format('forgetting generations: %Index(gen,gens) done')

        self.repo = self.app.get_repository_object()

        # We lock everything. This is to avoid a race condition
        # between different clients doing backup and forget at the
        # same time. If we only lock the client we care about, plus
        # the chunk indexes, the following scenario is possible:
        #
        #       1. Client A locks itself, plus chunk indexes, and
        #          starts running forget, but slowly.
        #       2. Client B locks itself, and starts running a backup.
        #          It merrily uses chunks that A thinks are only used
        #          but A itself, since B hasn't updated the chunk
        #          indexes, and can't do that before A is done.
        #       3. Client A finishes doing forget, and removes a number
        #          of chunks, because nobody else was marked as using
        #          them. However, some of these chunks are now being
        #          used by B.
        #       4. A commits its changes.
        #       5. B gains lock to chunk indexes, and commits its changes.
        #
        # At this point, the chunk indexes indicate that B uses some chunks,
        # but A already removed the chunks.
        #
        # By locking all clients during a forget, we prevent this race
        # condition: nobody else can be running a backup while anyone is
        # running a forget. We also lock the client list to prevent a new
        # client from being added.
        #
        # This is not a great solution, as it means that during a
        # forget (which currently can be quite slow) nobody can do a
        # backup. However, correctness trumps speed.

        self.repo.lock_client_list()
        client_names = self.repo.get_client_names()
        for some_client_name in client_names:
            self.repo.lock_client(some_client_name)
        self.repo.lock_chunk_indexes()

        self.app.dump_memory_profile('at beginning')
        client_name = self.app.settings['client-name']
        if args:
            self.app.ts['gens'] = args
            for genspec in args:
                self.app.ts['gen'] = genspec
                genid = self.repo.interpret_generation_spec(
                    client_name, genspec)
                self.app.ts.notify(
                    'Forgetting generation %s' % 
                    self.repo.make_generation_spec(genid))
                self.remove(genid)
                self.app.dump_memory_profile(
                    'after removing %s' % 
                    self.repo.make_generation_spec(genid))
        elif self.app.settings['keep']:
            genlist = []
            dt = datetime.datetime(1970, 1, 1, 0, 0, 0)
            for genid in self.repo.get_client_generation_ids(client_name):
                start = self.repo.get_generation_key(
                    genid, obnamlib.REPO_GENERATION_STARTED)
                end = self.repo.get_generation_key(
                    genid, obnamlib.REPO_GENERATION_ENDED)
                genlist.append((genid, dt.fromtimestamp(end)))

            fp = obnamlib.ForgetPolicy()
            rules = fp.parse(self.app.settings['keep'])
            keeplist = fp.match(rules, genlist)
            keepids = set(genid for genid, dt in keeplist)
            removeids = [genid
                         for genid, dt in genlist
                         if genid not in keepids]

            self.app.ts['gens'] = removeids
            for genid in removeids:
                self.app.ts['gen'] = genid
                self.remove(genid)
                self.app.dump_memory_profile(
                    'after removing %s' % 
                    self.repo.make_generation_spec(genid))

        # Commit or unlock everything.
        self.repo.unlock_client_list()
        for some_client_name in client_names:
            if some_client_name == client_name:
                self.repo.commit_client(some_client_name)
            else:
                self.repo.unlock_client(some_client_name)
        self.repo.commit_chunk_indexes()
        self.app.dump_memory_profile('after committing')

        self.repo.close()
        self.app.ts.finish()

    def remove(self, genid):
        if self.app.settings['pretend']:
            self.app.ts.notify(
                'Pretending to remove generation %s' % 
                self.repo.make_generation_spec(genid))
        else:
            self.repo.remove_generation(genid)
