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


import fcntl
import signal
import struct
import sys
import termios
import time

import obnamlib


class TerminalStatus(object):

    '''Update status to terminal.
    
    This is not the plugin itself, this just takes care of updating things
    to the terminal.
    
    '''
    
    def __init__(self):
        self.written = ''
        self.cached = ''
        self.when = 0
        self.freq = 1.0
        
        self.width = self.get_terminal_width() - 1
        signal.signal(signal.SIGWINCH, self.sigwinch_handler)

    def get_terminal_width(self):
        '''Return width of terminal in characters.

        If this fails, assume 80.
        
        Borrowed and adapted from bzrlib.
        
        '''
        
        try:
            s = struct.pack('HHHH', 0, 0, 0, 0)
            x = fcntl.ioctl(1, termios.TIOCGWINSZ, s)
            return struct.unpack('HHHH', x)[1]
        except IOError:
            return 80

    def sigwinch_handler(self, signum, frame):
        # Clear the terminal from old stuff, using the old width.
        self.clear()
        # Subtract one from actual terminal width to avoid wrapping
        # by printing to the last character position in the line.
        self.width = self.get_terminal_width() - 1

    def raw_write(self, msg):
        if sys.stdout.isatty():
            sys.stdout.write('\b \b' * len(self.written))
            sys.stdout.write(msg)
            sys.stdout.flush()
            self.written = msg
    
    def write(self, msg, force=False):
        msg = msg[:self.width]
        if force:
            self.raw_write(msg)
        else:
            now = time.time()
            if now - self.when >= self.freq:
                self.raw_write(msg)
                self.when = now
        self.cached = msg

    def clear(self):
        self.write('', force=True)

    def progress(self, message):
        self.write('%s' % message)

    def notify(self, message):
        cached = self.cached
        self.clear()
        sys.stdout.write('%s\n' % message)
        sys.stdout.flush()
        self.write(cached, force=True)

    def finished(self):
        if self.cached:
            self.write(self.cached, force=True)
            sys.stdout.write('\n')
        sys.stdout.flush()


class TerminalStatusPlugin(obnamlib.ObnamPlugin):

    units = [
        (2**30, 'GiB'),
        (2**20, 'MiB'),
        (2**10, 'KiB'),
        (0, 'B'),
    ]

    def enable(self):
        self.ts = TerminalStatus()
        self.app.hooks.new('status')
        self.app.hooks.new('progress-found-file')
        self.app.hooks.new('progress-data-done')
        self.app.hooks.new('error-message')
        self.add_callback('status', self.status_cb)
        self.add_callback('progress-found-file', self.found_file_cb)
        self.add_callback('progress-data-done', self.data_done_cb)
        self.add_callback('error-message', self.error_message_cb)
        self.add_callback('shutdown', self.ts.finished)
        self.app.config.new_boolean(['quiet'], 'be silent')
        self.current = ''
        self.num_files = 0
        self.total_data = 0
        self.data_done = 0
        
    def disable(self):
        self.ts = None

    def found_file_cb(self, filename, size):
        self.current = filename
        self.num_files += 1
        self.total_data += size
        self.update()
        
    def data_done_cb(self, amount):
        self.data_done += amount
        self.update()

    def status_cb(self, msg):
        if not self.app.config['quiet']:
            self.ts.notify(msg)

    def error_message_cb(self, msg):
        if self.app.config['quiet']:
            sys.stderr.write('Error: %s\n' % msg)
        else:
            self.ts.clear()
            sys.stderr.write('Error: %s\n' % msg)
            self.update()

    def find_unit(self, bytes):
        for factor, unit in self.units:
            if bytes >= factor:
                return factor, unit
        
    def scale(self, factor, bytes):
        if factor > 0:
            return '%.1f' % (float(bytes) / float(factor))
        else:
            return '0'

    def update(self):
        if self.app.config['quiet']:
            return
        factor, unit = self.find_unit(min(self.total_data, self.data_done))
        total = self.scale(factor, self.total_data)
        done = self.scale(factor, self.data_done)
        if self.current:
            tail = ' now: %s' % self.current
        else:
            tail = ''
        self.ts.progress('%d files, %s/%s %s%s' %
                         (self.num_files, done, total, unit, tail))

