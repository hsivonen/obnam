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


import datetime

import obnamlib


class ForgetPlugin(obnamlib.ObnamPlugin):

    '''Forget generations.'''
    
    def enable(self):
        self.app.add_subcommand('forget', self.forget,
                                arg_synopsis='[GENERATION]...')
        self.app.settings.string(['keep'],
                                  'policy for what generations to keep '
                                  'when forgetting')

    def forget(self, args):
        '''Forget (remove) specified backup generations.'''
        self.app.settings.require('repository')
        self.app.settings.require('client-name')
        
        self.app.ts['gen'] = None
        self.app.ts['gens'] = []
        self.app.ts.format('forgetting generations: %Index(gen,gens) done')

        self.repo = self.app.open_repository()
        self.repo.lock_client(self.app.settings['client-name'])
        self.repo.lock_shared()

        self.app.dump_memory_profile('at beginning')
        if args:
            self.app.ts['gens'] = args
            for genspec in args:
                self.app.ts['gen'] = genspec
                genid = self.repo.genspec(genspec)
                self.app.ts.notify('Forgetting generation %s' % genid)
                self.remove(genid)
                self.app.dump_memory_profile('after removing %s' % genid)
        elif self.app.settings['keep']:
            genlist = []
            dt = datetime.datetime(1970, 1, 1, 0, 0, 0)
            for genid in self.repo.list_generations():
                start, end = self.repo.get_generation_times(genid)
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
                self.app.dump_memory_profile('after removing %s' % genid)

        self.repo.commit_client()
        self.repo.commit_shared()
        self.app.dump_memory_profile('after committing')
        self.repo.fs.close()
        self.app.ts.finish()

    def remove(self, genid):
        if self.app.settings['pretend']:
            self.app.ts.notify('Pretending to remove generation %s' % genid)
        else:
            self.repo.remove_generation(genid)

