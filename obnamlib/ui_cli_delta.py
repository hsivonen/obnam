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


class DeltaCommand(obnamlib.CommandLineCommand):

    """Compute rsync delta for a file on the filesystem."""

    def delta(self, options, args):
        of = obnamlib.ObjectFactory()
        data = file(args[0]).read()
        parts = []
        pos = 0
        while pos < len(data):
            part, pos = of.decode_object(data, pos)
            parts.append(part)
        
        deltagen = obnamlib.RsyncDeltaGenerator()
        f = file(args[1])
        for x in deltagen.file_delta(parts, f, options.blocksize):
            sys.stdout.write(of.encode_component(x))
        f.close()

    def run(self, options, args, progress): # pragma: no cover
        self.delta(options, args)

