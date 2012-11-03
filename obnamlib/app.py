# Copyright (C) 2009, 2011  Lars Wirzenius
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


class App(cliapp.Application):

    '''Main program for backup program.'''
    
    def add_settings(self):
        devel_group = obnamlib.option_group['devel']
        perf_group = obnamlib.option_group['perf']
    
        self.settings.string(['repository', 'r'], 'name of backup repository')

        self.settings.string(['client-name'], 'name of client (%default)',
                           default=self.deduce_client_name())

        self.settings.bytesize(['node-size'],
                             'size of B-tree nodes on disk; only affects new '
                                'B-trees so you may need to delete a client '
                                'or repository to change this for existing '
                                'repositories '
                                 '(default: %default)',
                              default=obnamlib.DEFAULT_NODE_SIZE,
                              group=perf_group)

        self.settings.bytesize(['chunk-size'],
                            'size of chunks of file data backed up '
                                 '(default: %default)',
                             default=obnamlib.DEFAULT_CHUNK_SIZE,
                              group=perf_group)

        self.settings.bytesize(['upload-queue-size'],
                            'length of upload queue for B-tree nodes '
                                 '(default: %default)',
                            default=obnamlib.DEFAULT_UPLOAD_QUEUE_SIZE,
                            group=perf_group)

        self.settings.bytesize(['lru-size'],
                             'size of LRU cache for B-tree nodes '
                                 '(default: %default)',
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

        self.settings.boolean(['quiet'], 'be silent')
        self.settings.boolean(['verbose'], 'be verbose')

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

        self.pm = obnamlib.PluginManager()
        self.pm.locations = [self.plugins_dir()]
        self.pm.plugin_arguments = (self,)
        
        self.setup_hooks()

        self.fsf = obnamlib.VfsFactory()

        self.pm.load_plugins()
        self.pm.enable_plugins()
        self.hooks.call('plugins-loaded')

    def deduce_client_name(self):
        return socket.gethostname()

    def setup_hooks(self):
        self.hooks = obnamlib.HookManager()
        self.hooks.new('plugins-loaded')
        self.hooks.new('config-loaded')
        self.hooks.new('shutdown')

        # The Repository class defines some hooks, but the class
        # won't be instantiated until much after plugins are enabled,
        # and since all hooks must be defined when plugins are enabled,
        # we create one instance here, which will immediately be destroyed.
        # FIXME: This is fugly.
        obnamlib.Repository(None, 1000, 1000, 100, self.hooks, 10, 10, 10,
                            self.time, 0, '')

    def plugins_dir(self):
        return os.path.join(os.path.dirname(obnamlib.__file__), 'plugins')

    def setup_logging(self):
        log = self.settings['log']
        if log and log != 'syslog' and not os.path.exists(log):
            fd = os.open(log, os.O_WRONLY | os.O_CREAT, 0600)
            os.close(fd)
        cliapp.Application.setup_logging(self)

    def process_args(self, args):
        try:
            if self.settings['quiet']:
                self.ts.disable()
            self.log_config()
            for pattern in self.settings['trace']:
                tracing.trace_add_pattern(pattern)
            self.hooks.call('config-loaded')
            cliapp.Application.process_args(self, args)
            self.hooks.call('shutdown')
            logging.info('Obnam ends')
        except larch.Error, e:
            logging.critical(str(e))
            sys.stderr.write('ERROR: %s\n' % str(e))
            sys.exit(1)

    def log_config(self):
        '''Log current configuration into the log file.'''
        f = StringIO.StringIO()
        self.settings.dump_config(f)
        logging.debug('Current configuration:\n%s' % f.getvalue())

    def setup_ttystatus(self):
        self.ts = ttystatus.TerminalStatus(period=0.01)
        if self.settings['quiet']:
            self.ts.disable()

    def open_repository(self, create=False, repofs=None): # pragma: no cover
        logging.debug('opening repository (create=%s)' % create)
        tracing.trace('repofs=%s' % repr(repofs))
        repopath = self.settings['repository']
        if repofs is None:
            repofs = self.fsf.new(repopath, create=create)
            if self.settings['crash-limit'] > 0:
                repofs.crash_limit = self.settings['crash-limit']
            repofs.connect()
        else:
            repofs.reinit(repopath)
        return obnamlib.Repository(repofs, 
                                    self.settings['node-size'],
                                    self.settings['upload-queue-size'],
                                    self.settings['lru-size'],
                                    self.hooks,
                                    self.settings['idpath-depth'],
                                    self.settings['idpath-bits'],
                                    self.settings['idpath-skip'],
                                    self.time,
                                    self.settings['lock-timeout'],
                                    self.settings['client-name'])

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

