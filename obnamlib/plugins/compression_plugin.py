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

class DeflateCompressionFilter(object):

    def __init__(self, app):
        self.tag = "deflate"
        self.app = app
        self.warned = False

    def filter_read(self, data, repo, toplevel):
        return zlib.decompress(data)

    def filter_write(self, data, repo, toplevel):
        how = self.app.settings['compress-with']
        if how == 'deflate':
            data = zlib.compress(data)
        elif how == 'gzip':
            if not self.warned:
                self.app.ts.notify("--compress-with=gzip is deprecated.  " +
                                   "Use --compress-with=deflate instead")
                self.warned = True
            data = zlib.compress(data)

        return data


class CompressionPlugin(obnamlib.ObnamPlugin):

    def enable(self):
        self.app.settings.choice(['compress-with'],
                                 ['none', 'deflate', 'gzip'],
                                 'use PROGRAM to compress repository with '
                                    '(one of none, deflate)',
                                 metavar='PROGRAM')

        hooks = [
            ('repository-data', DeflateCompressionFilter(self.app),
             obnamlib.Hook.EARLY_PRIORITY),
        ]
        for name, callback, prio in hooks:
            self.app.hooks.add_callback(name, callback, prio)
