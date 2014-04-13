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


import cliapp
import larch
import logging
import os
import socket
import StringIO
import sys
import time
import tracing
import ttystatus

import obnamlib


class ObnamIOError(obnamlib.ObnamError):

    msg = 'I/O error: {filename}: {errno}: {strerror}'


class ObnamSystemError(obnamlib.ObnamError):

    msg = 'System error: {filename}: {errno}: {strerror}'


class App(cliapp.Application):

    '''Main program for backup program.'''

    def add_settings(self):
        devel_group = obnamlib.option_group['devel']
        perf_group = obnamlib.option_group['perf']

        self.settings.string(['repository', 'r'], 'name of backup repository')

        self.settings.string(
            ['client-name'],
            'name of client (defaults to hostname)',
            default=self.deduce_client_name())

        self.settings.bytesize(['node-size'],
                             'size of B-tree nodes on disk; only affects new '
                                'B-trees so you may need to delete a client '
                                'or repository to change this for existing '
                                'repositories',
                              default=obnamlib.DEFAULT_NODE_SIZE,
                              group=perf_group)

        self.settings.bytesize(['chunk-size'],
                            'size of chunks of file data backed up',
                             default=obnamlib.DEFAULT_CHUNK_SIZE,
                              group=perf_group)

        self.settings.bytesize(['upload-queue-size'],
                            'length of upload queue for B-tree nodes',
                            default=obnamlib.DEFAULT_UPLOAD_QUEUE_SIZE,
                            group=perf_group)

        self.settings.bytesize(['lru-size'],
                             'size of LRU cache for B-tree nodes',
                             default=obnamlib.DEFAULT_LRU_SIZE,
                             group=perf_group)

        self.settings.string_list(['trace'],
                                'add to filename patters for which trace '
                                'debugging logging happens')


        self.settings.integer(['idpath-depth'],
                              'depth of chunk id mapping',
                              default=obnamlib.IDPATH_DEPTH,
                              group=perf_group)
        self.settings.integer(['idpath-bits'],
                              'chunk id level size',
                              default=obnamlib.IDPATH_BITS,
                              group=perf_group)
        self.settings.integer(['idpath-skip'],
                              'chunk id mapping lowest bits skip',
                              default=obnamlib.IDPATH_SKIP,
                              group=perf_group)

        self.settings.boolean(
            ['quiet'],
            'be silent: show only error messages, no progress updates')
        self.settings.boolean(
            ['verbose'],
            'be verbose: tell the user more of what is going on and '
            'generally make sure the user is aware of what is happening '
            'or at least that something is happening and '
            'also make sure their screen is getting updates frequently '
            'and that there is changes happening all the time so they '
            'do not get bored and that they in fact get frustrated by '
            'getting distracted by so many updates that they will move '
            'into the Gobi desert to live under a rock')

        self.settings.boolean(['pretend', 'dry-run', 'no-act'],
                           'do not actually change anything (works with '
                           'backup, forget and restore only, and may only '
                           'simulate approximately real behavior)')

        self.settings.string(['pretend-time'],
                             'pretend it is TIMESTAMP (YYYY-MM-DD HH:MM:SS); '
                                'this is only useful for testing purposes',
                             metavar='TIMESTAMP',
                             group=devel_group)

        self.settings.integer(['lock-timeout'],
                              'when locking in the backup repository, '
                                'wait TIMEOUT seconds for an existing lock '
                                'to go away before giving up',
                              metavar='TIMEOUT',
                              default=60)

        self.settings.integer(['crash-limit'],
                              'artificially crash the program after COUNTER '
                                'files written to the repository; this is '
                                'useful for crash testing the application, '
                                'and should not be enabled for real use; '
                                'set to 0 to disable (disabled by default)',
                              metavar='COUNTER',
                              group=devel_group)

        # The following needs to be done here, because it needs
        # to be done before option processing. This is a bit ugly,
        # but the best we can do with the current cliapp structure.
        # Possibly cliapp will provide a better hook for us to use
        # later on, but this is reality now.

        self.setup_ttystatus()

        self.fsf = obnamlib.VfsFactory()
        self.repo_factory = obnamlib.RepositoryFactory()

        self.setup_hooks()

        self.settings['log-level'] = 'info'

    def deduce_client_name(self):
        return socket.gethostname()

    def setup_hooks(self):
        self.hooks = obnamlib.HookManager()
        self.hooks.new('config-loaded')
        self.hooks.new('shutdown')

        # The repository factory creates all repository related hooks.
        self.repo_factory.setup_hooks(self.hooks)

    def setup(self):
        self.pluginmgr.plugin_arguments = (self,)

    def process_args(self, args):
        try:
            try:
                if self.settings['quiet']:
                    self.ts.disable()
                for pattern in self.settings['trace']:
                    tracing.trace_add_pattern(pattern)
                self.hooks.call('config-loaded')
                cliapp.Application.process_args(self, args)
                self.hooks.call('shutdown')
            except IOError as e:
                raise ObnamIOError(
                    errno=e.errno, strerror=e.strerror, filename=e.filename)
            except OSError as e:
                raise ObnamSystemError(
                    errno=e.errno, strerror=e.strerror, filename=e.filename)
        except larch.Error as e:
            logging.critical(str(e))
            sys.stderr.write('ERROR: %s\n' % str(e))
            sys.exit(1)
        except obnamlib.StructuredError as e:
            logging.critical(str(e))
            sys.stderr.write('ERROR: %s\n' % str(e))
            sys.exit(1)

    def setup_ttystatus(self):
        self.ts = ttystatus.TerminalStatus(period=0.1)
        if self.settings['quiet']:
            self.ts.disable()

    def get_repository_object(self, create=False, repofs=None):
        '''Return an implementation of obnamlib.RepositoryInterface.'''

        logging.info('Opening repository: %s', self.settings['repository'])
        tracing.trace('create=%s', create)
        tracing.trace('repofs=%s', repofs)

        repopath = self.settings['repository']
        if repofs is None:
            repofs = self.fsf.new(repopath, create=create)
            if self.settings['crash-limit'] > 0:
                repofs.crash_limit = self.settings['crash-limit']
            repofs.connect()
        else:
            repofs.reinit(repopath)

        kwargs = {
            'lock_timeout': self.settings['lock-timeout'],
            'node_size': self.settings['node-size'],
            'upload_queue_size': self.settings['upload-queue-size'],
            'lru_size': self.settings['lru-size'],
            'idpath_depth': self.settings['idpath-depth'],
            'idpath_bits': self.settings['idpath-bits'],
            'idpath_skip': self.settings['idpath-skip'],
            'hooks': self.hooks,
            'current_time': self.time,
            }

        if create:
            return self.repo_factory.create_repo(
                repofs, obnamlib.RepositoryFormat6, **kwargs)
        else:
            return self.repo_factory.open_existing_repo(repofs, **kwargs)

    def time(self):
        '''Return current time in seconds since epoch.

        This is a wrapper around time.time() so that it can be overridden
        with the --pretend-time setting.

        '''

        s = self.settings['pretend-time']
        if s:
            t = time.strptime(s, '%Y-%m-%d %H:%M:%S')
            return time.mktime(t)
        else:
            return time.time()

