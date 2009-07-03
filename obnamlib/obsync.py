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
import zlib


class Obsync(object):

    """A pure-Python implementation of the rsync algorithm.

    See http://www.samba.org/rsync/tech_report/ for an explanation of the
    rsync algorithm.

    This is not at all compatible with rsync the program, or rdiff,
    or librsync, or any other implementation of the rsync algorithm. It
    does not even implement the algorithm as described in the original
    paper. This is mostly because a) Python sucks as bit twiddling kinds
    of things, so we have chosen approaches that are fast in Python, and
    b) this is meant to be part of Obnam, a backup program, which changes
    the requirements of generic rsync a little bit.

    """
    
    def weak_checksum(self, data):
        """Compute weak checksum for data.
        
        Return obnamlib.Adler32 component.
        
        """
        
        return obnamlib.Adler32(str(zlib.adler32(data)))

    def strong_checksum(self, data):
        """Compute weak checksum for data.
        
        Return obnamlib.Md5 component.
        
        """

    def block_signature(self, block_data):
        """Compute rsync signature for a given block of data.
        
        Return an obnamlib.Checksums component.
        
        Assume the block is of whatever size the signatures should be
        computed for. It is the caller's responsibility to make sure
        all blocks in a signature file are of the same size.
        
        """
        
        return obnamlib.Checksums([])
        
    def file_signature(self, f, block_size):
        """Compute signatures for a file.
        
        Return a list of obnamlib.SyncSignature objects.
        
        """
        
        sigs = []
        while True:
            block = f.read(block_size)
            if not block:
                break
            sigs.append(self.block_signature(block))

        return sigs

