# Copyright (C) 2011  Lars Wirzenius
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
import zlib

import obnamlib


class CompressionPlugin(obnamlib.ObnamPlugin):

    def enable(self):
        self.app.settings.choice(['compress-with'],
                                 ['none', 'gzip'],
                                 'use PROGRAM to compress repository with '
                                    '(one of none, gzip)',
                                 metavar='PROGRAM')
        
        hooks = [
            ('repository-read-data', self.toplevel_read_data, True),
            ('repository-write-data', self.toplevel_write_data, False),
        ]
        for name, callback, rev in hooks:
            self.app.hooks.add_callback(name, callback, reverse=rev)

    def toplevel_read_data(self, data, repo, toplevel):
        how = self.app.settings['compress-with']
        if how == 'none':
            return data
        elif how == 'gzip':
            return zlib.decompress(data)
        assert False

    def toplevel_write_data(self, data, repo, toplevel):
        how = self.app.settings['compress-with']
        if how == 'none':
            return data
        elif how == 'gzip':
            return zlib.compress(data)
        assert False

