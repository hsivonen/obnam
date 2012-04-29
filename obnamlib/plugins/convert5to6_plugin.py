# Copyright (C) 2012  Lars Wirzenius
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
import re
import stat
import tracing
import zlib

import obnamlib


class Convert5to6Plugin(obnamlib.ObnamPlugin):

    '''Convert a version 5 repository to version 6, in place.'''

    def enable(self):
        self.app.add_subcommand('convert5to6', self.convert, arg_synopsis='')

    def convert(self, args):
        self.app.settings.require('repository')

        self.rawfs = self.app.fsf.new(self.app.settings['repository'])
        self.convert_format()
        self.repo = self.app.open_repository()
        self.convert_files()

    def convert_files(self):
        funcs = []
        if self.app.settings['compress-with'] == 'gzip':
            funcs.append(self.gunzip)
        if self.app.settings['encrypt-with']:
            self.symmetric_keys = {}
            funcs.append(self.decrypt)
        tracing.trace('funcs=%s' % repr(funcs))

        for filename in self.find_files():
            logging.debug('converting file %s' % filename)
            data = self.rawfs.cat(filename)
            tracing.trace('old data is %d bytes' % len(data))
            for func in funcs:
                data = func(filename, data)
            tracing.trace('new data is %d bytes' % len(data))
            self.repo.fs.overwrite_file(filename, data)

    def find_files(self):
        ignored_pat = re.compile(r'^(tmp.*|lock|format|userkeys|key)$')
        for filename, st in self.rawfs.scan_tree('.'):
            ignored = ignored_pat.match(os.path.basename(filename))
            if stat.S_ISREG(st.st_mode) and not ignored:
                assert filename.startswith('./')
                yield filename[2:]

    def get_symmetric_key(self, filename):
        toplevel = filename.split('/')[0]
        tracing.trace('toplevel=%s' % toplevel)

        if toplevel not in self.symmetric_keys:
            encoded = self.rawfs.cat(os.path.join(toplevel, 'key'))
            key = obnamlib.decrypt_with_secret_keys(encoded)
            self.symmetric_keys[toplevel] = key
        return self.symmetric_keys[toplevel]

    def decrypt(self, filename, data):
        symmetric_key = self.get_symmetric_key(filename)
        return obnamlib.decrypt_symmetric(data, symmetric_key)

    def gunzip(self, filename, data):
        return zlib.decompress(data)
        
    def convert_format(self):
        self.rawfs.overwrite_file('metadata/format', '6\n')

