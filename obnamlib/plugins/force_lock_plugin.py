# Copyright (C) 2009-2014  Lars Wirzenius
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


class RepositoryAccessError(obnamlib.ObnamError):

    msg = 'Repository does not exist or cannot be accessed: {error}'


class ForceLockPlugin(obnamlib.ObnamPlugin):

    def enable(self):
        self.app.add_subcommand('force-lock', self.force_lock)
        self.app.add_subcommand('_lock', self.lock, hidden=True)

    def force_lock(self, args):
        '''Force a locked repository to be open.'''

        self.app.settings.require('repository')

        repourl = self.app.settings['repository']
        client_name = self.app.settings['client-name']
        logging.info('Forcing lock')
        logging.info('Repository: %s' % repourl)

        try:
            repo = self.app.get_repository_object()
        except OSError, e:
            raise RepositoryAccessError(error=str(e))

        repo.force_client_list_lock()
        for client_name in repo.get_client_names():
            repo.force_client_lock(client_name)
        repo.force_chunk_indexes_lock()

        repo.close()

        return 0

    def lock(self, args):
        '''Add locks to the repository.

        This is a hidden command meant for use in testing only.

        '''

        self.app.settings.require('repository')

        repourl = self.app.settings['repository']
        client_name = self.app.settings['client-name']
        logging.info('Creating lock')
        logging.info('Repository: %s' % repourl)
        logging.info('Client: %s' % client_name)

        try:
            repo = self.app.get_repository_object()
        except OSError, e:
            raise RepositoryAccessError(error=str(e))

        repo.lock_client_list()
        if client_name:
            repo.lock_client(client_name)
        repo.lock_chunk_indexes()

        repo.close()

        return 0
