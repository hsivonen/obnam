# Copyright (C) 2009, 2010, 2011  Lars Wirzenius
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

import obnamlib


class ForceLockPlugin(obnamlib.ObnamPlugin):

    def enable(self):
        self.app.add_subcommand('force-lock', self.force_lock)

    def force_lock(self, args):
        '''Force a locked repository to be open.'''
        self.app.settings.require('repository')
        self.app.settings.require('client-name')

        repourl = self.app.settings['repository']
        client_name = self.app.settings['client-name']
        logging.info('Forcing lock')
        logging.info('Repository: %s' % repourl)
        logging.info('Client: %s' % client_name)

        try:
            repo = self.app.open_repository()
        except OSError, e:
            raise obnamlib.Error('Repository does not exist '
                                  'or cannot be accessed.\n' +
                                  str(e))

        all_clients = repo.list_clients()
        if client_name not in all_clients:
            msg = 'Client does not exist in repository.'
            logging.warning(msg)
            self.app.output.write('Warning: %s\n' % msg)
            return

        all_dirs = ['clientlist', 'chunksums', 'chunklist', 'chunks', '.']
        for client_name in all_clients:
            client_id = repo.clientlist.get_client_id(client_name)
            client_dir = repo.client_dir(client_id)
            all_dirs.append(client_dir)

        for one_dir in all_dirs:
            lockname = os.path.join(one_dir, 'lock')
            if repo.fs.exists(lockname):
                logging.info('Removing lockfile %s' % lockname)
                repo.fs.remove(lockname)
            else:
                logging.info('%s is not locked' % one_dir)

        repo.fs.close()

        return 0
