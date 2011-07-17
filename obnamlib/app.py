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
import logging
import os
import socket
import tracing
import sys

import obnamlib


class App(cliapp.Application):

    '''Main program for backup program.'''
    
    def __init__(self):
        cliapp.Application.__init__(self)

        self.setup_config()        

        self.pm = obnamlib.PluginManager()
        self.pm.locations = [self.plugins_dir()]
        self.pm.plugin_arguments = (self,)
        
        self.interp = obnamlib.Interpreter()
        self.register_command = self.interp.register

        self.setup_hooks()

        self.fsf = obnamlib.VfsFactory()

    @property
    def default_config_file(self):
        if os.getuid() == 0:
            return '/var/log/obnam.log'
        else:
            cache = (os.environ.get('XDG_CACHE_HOME', '') or
                     os.path.expanduser('~/.cache'))
            return os.path.join(cache, 'obnam', 'obnam.log')

    def setup_config(self):
        self.config = self.settings

        self.config.string(['repository', 'r'], 'name of backup repository')

        self.config.string(['client-name'], 'name of client (%default)',
                           default=self.deduce_client_name())

        self.config.boolean(['pretend', 'dry-run', 'no-act'],
                           'do not write or remove anything, just '
                                'pretend to do that')

        self.config.bytesize(['node-size'],
                             'size of B-tree nodes on disk '
                                 '(default: %default)',
                              default=obnamlib.DEFAULT_NODE_SIZE)

        self.config.bytesize(['chunk-size'],
                            'size of chunks of file data backed up '
                                 '(default: %default)',
                             default=obnamlib.DEFAULT_CHUNK_SIZE)

        self.config.bytesize(['upload-queue-size'],
                            'length of upload queue for B-tree nodes '
                                 '(default: %default)',
                            default=obnamlib.DEFAULT_UPLOAD_QUEUE_SIZE)

        self.config.bytesize(['lru-size'],
                             'size of LRU cache for B-tree nodes '
                                 '(default: %default)',
                             default=obnamlib.DEFAULT_LRU_SIZE)

        self.config.choice(['dump-memory-profile'],
                           ['simple', 'none', 'meliae', 'heapy'],
                           'make memory profiling dumps '
                                'after each checkpoint and at end? '
                                'set to none, simple, meliae, or heapy '
                                '(default: %default)')

        self.config.string_list(['trace'],
                                'add to filename patters for which trace '
                                'debugging logging happens')
        
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
        obnamlib.Repository(None, 1000, 1000, 100, self.hooks)

    def plugins_dir(self):
        return os.path.join(os.path.dirname(obnamlib.__file__), 'plugins')

    def rotate_logs(self, filename, keep):
        def rename(old_suffix, counter):
            new_suffix = '.%d' % counter
            if os.path.exists(filename + new_suffix):
                if counter < keep:
                    rename(new_suffix, counter + 1)
                else:
                    os.remove(filename + new_suffix)
            os.rename(filename + old_suffix, filename + new_suffix)
        rename('', 0)

    def setup_logging(self):
        log_filename = self.config['log']
        log_max = self.config['log-max']
        log_keep = int(self.config['log-keep'])
        if (os.path.exists(log_filename) and 
            os.path.getsize(log_filename) > log_max):
            self.rotate_logs(log_filename, log_keep)
        if os.getuid() != 0:
            log_dir = os.path.dirname(log_filename)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir)
        
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
        handler = logging.FileHandler(self.config['log'])
        handler.setFormatter(formatter)
        logger = logging.getLogger()
        levels = {
            'debug': logging.DEBUG,
            'info': logging.INFO,
            'warning': logging.WARNING,
            'error': logging.ERROR,
            'critical': logging.CRITICAL,
        }
        level_name = self.config['log-level']
        level = levels.get(level_name.lower(), logging.DEBUG)
        logger.setLevel(level)
        logger.addHandler(handler)
        
        for pattern in self.config['trace']:
            tracing.trace_add_pattern(pattern)
        
    def run(self):
        self.pm.load_plugins()
        self.pm.enable_plugins()
        self.hooks.call('plugins-loaded')
        self.settings.load_configs()
        args = self.settings.parse_args(sys.argv[1:])
        self.hooks.call('config-loaded')
        self.setup_logging()
        logging.info('Obnam %s starts' % obnamlib.version)
        if args:
            logging.info('Executing command: %s' % args[0])
            self.interp.execute(args[0], args[1:])
        else:
            raise obnamlib.AppException('Usage error: '
                                        'must give operation on command line')
        self.hooks.call('shutdown')
        logging.info('Obnam ends')

    def open_repository(self, create=False): # pragma: no cover
        repopath = self.config['repository']
        repofs = self.fsf.new(repopath, create=create)
        repofs.connect()
        return obnamlib.Repository(repofs, 
                                    self.config['node-size'],
                                    self.config['upload-queue-size'],
                                    self.config['lru-size'],
                                    self.hooks)

    def require(self, setting):
        '''Make sure the named option is set.'''
        
        if not self.settings[setting]:
            raise obnamlib.Error('you must use option --%s' % setting)

