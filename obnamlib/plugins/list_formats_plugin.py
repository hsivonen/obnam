# Copyright (C) 2015  Lars Wirzenius
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


import obnamlib


class ListFormatsPlugin(obnamlib.ObnamPlugin):

    def enable(self):
        self.app.add_subcommand(
            'list-formats',
            self.list_formats,
            arg_synopsis='')

    def list_formats(self, args):
        factory = obnamlib.RepositoryFactory()
        formats = factory.get_implementation_classes()
        for format_class in formats:
            self.app.output.write('%s\n' % format_class.format)
