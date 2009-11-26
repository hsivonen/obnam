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


import sys
import time

import obnamlib


class TerminalStatus(object):

    '''Update status to terminal.
    
    This is not the plugin itself, this just takes care of updating things
    to the terminal.
    
    '''
    
    def __init__(self):
        self.written = ''
        self.when = 0
        self.freq = 1.0
        self.width = 79 # FIXME: Should query terminal and react to SIGWINCH

    def raw_write(self, msg):
        if sys.stdout.isatty():
            sys.stdout.write('\b \b' * len(self.written))
            sys.stdout.write(msg)
            sys.stdout.flush()
    
    def write(self, msg, force=False):
        msg = msg[:self.width]
        if force:
            self.raw_write(msg)
        else:
            now = time.time()
            if now - self.when >= self.freq:
                self.raw_write(msg)
                self.when = now
        self.written = msg

    def clear(self):
        self.write('', force=True)

    def progress(self, percent, message):
        self.write('%.1f %% %s' % (float(percent), message))

    def notify(self, message):
        written = self.written
        self.clear()
        sys.stdout.write('%s\n' % message)
        sys.stdout.flush()
        self.write(written, force=True)

    def finished(self):
        self.write(self.written, force=True)
        sys.stdout.write('\n')
        sys.stdout.flush()


class TerminalStatusPlugin(obnamlib.ObnamPlugin):

    def enable(self):
        self.ts = TerminalStatus()
        self.app.hooks.new('status')
        self.add_callback('status', self.ts.notify)
        self.add_callback('shutdown', self.ts.finished)
        
    def disable(self):
        self.ts = None

