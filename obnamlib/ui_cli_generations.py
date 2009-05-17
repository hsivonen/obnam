# Copyright (C) 2008  Lars Wirzenius <liw@liw.fi>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.


import sys

import obnamlib


class GenerationsCommand(obnamlib.CommandLineCommand):

    """A sub-command for the command line interface to list generations."""

    def generations(self, host_id, output=sys.stdout):
        """List all generations for a given host."""
        host = self.store.get_host(host_id)
        for genref in host.genrefs:
            output.write("%s\n" % genref)

    def run(self, config, args): # pragma: no cover
        host_id = args[0]
        store_url = args[1]

        self.store = obnamlib.Store(store_url, "w")

        self.generations(host_id)
