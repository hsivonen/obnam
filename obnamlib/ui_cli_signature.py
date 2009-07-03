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


class SignatureCommand(obnamlib.CommandLineCommand):

    """Compute rsync signature of a file on the filesystem."""

    def add_options(self, parser):
        parser.add_option("--rsync-block-size", metavar="SIZE", default=4096,
                          help="compute rsync signatures using blocks of size "
                               "SIZE (default %default bytes)")
    
    def signature(self, options, args):
        obsync = obnamlib.Obsync()
        f = file(args[0])
        rsyncsig = obsync.make_signature("obj_id", f, options.rsync_block_size)
        f.close()
        of = obnamlib.ObjectFactory()
        sys.stdout.write(of.encode_object(rsyncsig))

    def run(self, options, args, progress): # pragma: no cover
        self.signature(options, args)

