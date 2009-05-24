# Copyright (C) 2009  Lars Wirzenius <liw@liw.fi>
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


import stat
import sys

import obnamlib


class CatCommand(obnamlib.CommandLineCommand):

    """Show contents of a file from a given generation."""

    def cat(self, store, host_id, gen_id, pathname, output=sys.stdout,
            Lookupper=obnamlib.Lookupper):
        host = store.get_host(host_id)
        gen = store.get_object(host, gen_id)
        lookupper = Lookupper(store, host, gen)
        # The following will raise NotFound if pathname doesn't exist.
        # That's what we want.
        if lookupper.is_file(pathname):
            st, contref, sigref, deltaref, slink = lookupper.get_file(pathname)
            if stat.S_ISREG(st.st_mode):
                store.cat(host, output, contref, deltaref)
            else:
                raise obnamlib.Exception("Cannot output: "
                                         "%s is not a regular file" % 
                                         pathname)
        else:
            raise obnamlib.Exception("Cannot output: %s is a directory, "
                                     "not a file" % pathname)

    def run(self, options, args): # pragma: no cover
        pathname = args[0]
        store = obnamlib.Store(options.store, "r")
        self.cat(store, options.host, options.generation, pathname)
        store.close()
