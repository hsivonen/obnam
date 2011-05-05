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
        self.app.register_command('force-lock', self.force_lock)

    def force_lock(self, args):
        self.app.config.require('repository')
        self.app.config.require('client-name')

        repourl = self.app.config['repository']
        client_name = self.app.config['client-name']
        logging.info('Forcing lock')
        logging.info('Repository: %s' % repourl)
        logging.info('Client: %s' % client_name)

        try:
            repo = self.app.open_repository()
        except OSError, e:
            raise obnamlib.AppException('Repository does not exist '
                                         'or cannot be accessed.\n' +
                                         str(e))

        if client_name not in repo.list_clients():
            logging.warning('Client does not exist in repository.')
            return

        client_id = repo.clientlist.get_client_id(client_name)
        client_dir = repo.client_dir(client_id)        
        lockname = os.path.join(client_dir, 'lock')
        if repo.fs.exists(lockname):
            logging.info('Removing lockfile %s' % lockname)
            repo.fs.remove(lockname)
        else:
            logging.info('Client is not locked')

