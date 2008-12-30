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


class ShowGenerationsCommand(object):

    """Show contents of generations."""

    def show_filegroup(self, host, fgref, output=sys.stdout):
        fg = self.store.get_object(host, fgref)
        for file in fg.find(kind=obnamlib.FILE):
            output.write("%s\n" % file.first_string(kind=obnamlib.FILENAME))

    def show_dir(self, host, dirref, output=sys.stdout):
        dir = self.store.get_object(host, dirref)

        output.write("%s:\n" % dir.name)

        for fgref in dir.fgrefs:
            self.show_filegroup(host, fgref, output=output)
        output.write("\n")

        for subdirref in dir.dirrefs:
            self.show_dir(host, subdirref, output=output)

    def show_generations(self, host_id, genrefs, output=sys.stdout):
        """Show contents of the given generations."""

        host = self.store.get_host(host_id)

        for genref in genrefs:
            output.write("Generation %s:\n\n" % genref)

            gen = self.store.get_object(host, genref)

            if gen.fgrefs:
                for fgref in gen.fgrefs:
                    self.show_filegroup(host, fgref, output=output)

            for dirref in gen.dirrefs:
                self.show_dir(host, dirref, output=output)

    def __call__(self, config, args): # pragma: no cover
        host_id = args[0]
        store_url = args[1]
        genrefs = args[2:]

        self.store = obnamlib.Store(store_url, "w")

        self.show_generations(host_id, genrefs)
