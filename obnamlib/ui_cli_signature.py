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

    """Compute rsync signature."""
    
    def add_options(self, parser):
        parser.add_option("--rsync-block-size", metavar="SIZE", default=4096,
                          help="use blocks of size SIZE for rsync")
    
    def signature(self, options, args):
        """Compute rsync signature for an input file."""

        if len(args) != 1:
            raise obnamlib.Exception("signature wants exactly one argument")

        fsf = obnamlib.VfsFactory()
        dirname = os.path.dirname(args[0])
        basename = os.path.basename(args[0])
        fs = fsf.new(dirname)
        f = fs.open(basename)
        while True:
            block = f.read(options.rsync_block_size)
            if not block:
                break
            weak = obnamlib.Ob

    def run(self, options, args, progress): # pragma: no cover
        self.signature(options, args)

