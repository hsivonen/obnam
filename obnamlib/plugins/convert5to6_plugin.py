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
import stat
import ttystatus

import obnamlib


class Convert5to6Plugin(obnamlib.ObnamPlugin):

    '''Convert a version 5 repository to version 6, in place.'''

    def enable(self):
        self.app.add_subcommand('convert5to6', self.convert, arg_synopsis='')

    def convert(self, args):
        self.app.settings.require('repository')

        self.repo = self.app.open_repository()

        self.convert_chunks()
        self.convert_clients()
        self.convert_format()

        self.repo.fs.close()

    def convert_chunks(self):
        pass
        
    def convert_clients(self):
        pass

    def convert_format(self):
        pass

