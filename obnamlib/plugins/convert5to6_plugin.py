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
import zlib

import obnamlib


class Convert5to6Plugin(obnamlib.ObnamPlugin):

    '''Convert a version 5 repository to version 6, in place.'''

    def enable(self):
        self.app.add_subcommand('convert5to6', self.convert, arg_synopsis='')

    def convert(self, args):
        self.app.settings.require('repository')

        self.repo = self.app.open_repository()
        self.rawfs = self.repo.fs.fs
        self.convert_chunks()
        self.convert_format()

    def convert_chunks(self):
        funcs = []
        if self.app.settings['encrypt-with']:
            symmetric_key = self.get_symmetric_key()
            funcs.append(lambda data: self.decrypt(data, symmetric_key))
        if self.app.settings['compress-with'] == 'gzip':
            funcs.append(self.gunzip)

        chunkids = self.find_chunks()
        for chunkid in chunkids:
            logging.debug('converting chunk %s' % chunkid)
            data = self.rawfs.cat(filename)
            for func in funcs:
                data = func(data)
            self.repo.fs.write_file(filename, data)

    def find_chunks(self):
        pat = re.compile(r'^.*/.*/[0-9a-fA-F]+$')
        for filename, st in self.rawfs.scan_tree('chunks'):
            if stat.S_IFREG(st.st_mode) and pat.match(filename):
                yield filename

    def get_symmetric_key(self):
        encoded = self.rawfs.cat(os.path.join('chunks', 'key'))
        key = obnamlib.decrypt_with_secret_keys(encoded)
        return key

    def decrypt(self, data, symmetric_key):
        return obnamlib.decrypt_symmetric(data, symmetric_key)

    def gunzip(self, data):
        return zlib.decomrpess(data)
        
    def convert_format(self):
        pass

