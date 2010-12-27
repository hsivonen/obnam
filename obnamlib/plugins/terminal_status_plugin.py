# Copyright (C) 2009  Lars Wirzenius
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


import os
import stat
import ttystatus

import obnamlib


class TerminalStatusPlugin(obnamlib.ObnamPlugin):

    def enable(self):
        self.app.config.new_boolean(['quiet'], 'be silent')

        self.ts = ttystatus.TerminalStatus(period=0.25)
        self.ts['uploaded-bytes'] = 0

        self.app.hooks.new('status')
        self.app.hooks.new('progress-found-file')
        self.app.hooks.new('progress-data-uploaded')
        self.app.hooks.new('error-message')

        self.add_callback('status', self.status_cb)
        self.add_callback('progress-found-file', self.found_file_cb)
        self.add_callback('progress-data-uploaded', self.data_uploaded_cb)
        self.add_callback('error-message', self.error_message_cb)
        self.add_callback('config-loaded', self.config_loaded_cb)
        self.add_callback('shutdown', self.shutdown_cb)
        
    def disable(self):
        self.ts.finish()
        self.ts = None

    def config_loaded_cb(self):
        if not self.app.config['quiet']:
            self.ts.add(ttystatus.ElapsedTime())
            self.ts.add(ttystatus.Literal(' '))
            self.ts.add(ttystatus.Counter('current-file'))
            self.ts.add(ttystatus.Literal(' files; '))
            self.ts.add(ttystatus.ByteSize('uploaded-bytes'))
            self.ts.add(ttystatus.Literal(' up ('))
            self.ts.add(ttystatus.ByteSpeed('uploaded-bytes'))
            self.ts.add(ttystatus.Literal(') '))
            self.ts.add(ttystatus.Pathname('current-file'))

    def found_file_cb(self, filename, metadata):
        self.ts['current-file'] = filename
        if stat.S_ISDIR(metadata.st_mode):
            dirname = filename
        else:
            dirname = os.path.dirname(filename)
        if not dirname.endswith(os.sep):
            dirname += os.sep
        self.ts['current-dir'] = dirname
        self.ts['current-file'] = filename
        
    def data_uploaded_cb(self, amount):
        self.ts['uploaded-bytes'] += amount

    def status_cb(self, msg):
        if not self.app.config['quiet']:
            self.ts.notify(msg)

    def error_message_cb(self, msg):
        self.ts.notify('Error: %s' % msg)

    def shutdown_cb(self):
        self.ts.finish()
