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


import sys

import obnamlib


class PatchCommand(obnamlib.CommandLineCommand):

    """Apply an rsync delta file."""

    def patch(self, options, args):
        old_file = file(sys.argv[0])
    
        of = obnamlib.ObjectFactory()
        data = file(args[1]).read()
        rsyncdelta, pos = of.decode_object(data, 0)
        
        obsync = obnamlib.Obsync()
        obsync.patch(sys.stdout, old_file, rsyncdelta)

    def run(self, options, args, progress): # pragma: no cover
        self.patch(options, args)

