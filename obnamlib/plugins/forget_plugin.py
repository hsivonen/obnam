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
        self.app.register_command('forget', self.forget)
        self.app.config.new_string(['keep'],
                                   'policy for what generations to keep '
                                   'when forgetting')

    def forget(self, args):
        fs = self.app.fsf.new(self.app.config['store'])
        self.store = obnamlib.Store(fs)
        self.store.lock_host(self.app.config['hostname'])

        if args:
            for genid in args:
                self.remove(genid)
        elif self.app.config['keep']:
            genlist = []
            dt = datetime.datetime(1970, 1, 1, 0, 0, 0)
            for genid in self.store.list_generations():
                start, end = self.store.get_generation_times(genid)
                genlist.append((genid, dt.fromtimestamp(end)))

            fp = obnamlib.ForgetPolicy()
            rules = fp.parse(self.app.config['keep'])
            keeplist = fp.match(rules, genlist)
            keepids = set(genid for genid, dt in keeplist)

            for genid, dt in genlist:
                if genid not in keepids:
                    self.remove(genid)

        self.store.commit_host()

    def remove(self, genid):
        if self.app.config['pretend']:
            self.app.hooks.call('status', 'pretending to remove %s' % genid)
        else:
            self.store.remove_generation(genid)

