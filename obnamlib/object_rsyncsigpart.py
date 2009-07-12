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


import obnamlib


class RsyncSigPart(obnamlib.Object):

    """A (partial) rsync signature."""

    kind = obnamlib.RSYNCSIGPART

    def __init__(self, id, block_size=0, checksums=None):
        obnamlib.Object.__init__(self, id)
        self.components += [obnamlib.SigBlockSize(block_size)]
        if checksums:
            self.components += checksums
            
    @property
    def block_size(self):
        return self.find(kind=obnamlib.SIGBLOCKSIZE)[0].block_size
        
    @property
    def checksums(self):
        return self.find(kind=obnamlib.CHECKSUMS)

