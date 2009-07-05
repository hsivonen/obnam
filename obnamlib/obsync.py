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


import hashlib
import obnamlib
import zlib


class RsyncLookupTable(object):

    def __init__(self, compute_weak, compute_strong):
        self.compute_weak = compute_weak
        self.compute_strong = compute_strong
        self.dict = {}
        
    def add_checksums(self, checksums):
        for block_number, c in enumerate(checksums):
            weak = c.first_string(kind=obnamlib.ADLER32)
            strong = c.first_string(kind=obnamlib.MD5)
            if weak not in self.dict:
                self.dict[weak] = dict()
            self.dict[weak][strong] = block_number

    def __getitem__(self, block_data):
        weak = str(self.compute_weak(block_data))
        subdict = self.dict.get(weak)
        if subdict:
            strong = str(self.compute_strong(block_data))
            return subdict.get(strong)
        return None


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

        return obnamlib.Md5(hashlib.md5(data).digest())

    def block_signature(self, block_data):
        """Compute rsync signature for a given block of data.
        
        Return an obnamlib.Checksums component.
        
        Assume the block is of whatever size the signatures should be
        computed for. It is the caller's responsibility to make sure
        all blocks in a signature file are of the same size.
        
        """
        
        weak = self.weak_checksum(block_data)
        strong = self.strong_checksum(block_data)
        return obnamlib.Checksums([weak, strong])
        
    def file_signature(self, f, block_size):
        """Compute signatures for a file.
        
        Generate a list of obnamlib.Checksums objects.
        
        """
        
        while True:
            block = f.read(block_size)
            if not block:
                break
            yield self.block_signature(block)

    def file_delta(self, rsyncsigparts, new_file, chunk_size):
        """Compute delta from RsyncSigParts to new_file.
        
        Return a list of obnamlib.FileChunk and obnamlib.OldFileSubString
        objects.
        
        """

        block_size = rsyncsigparts[0].block_size
        lookup_table = RsyncLookupTable(self.weak_checksum,
                                        self.strong_checksum)
        for part in rsyncsigparts:
            lookup_table.add_checksums(part.checksums)

        # First we collect just the raw data as single-character strings
        # and block numbers plus lengths in the old file. We'll optimize 
        # this list later.
        
        output = []
        assert block_size > 0
        block_data = new_file.read(block_size)
        while block_data:
            block_number = lookup_table[block_data]
            if block_number is None:
                output.append(block_data[0])
                block_data = block_data[1:]
                byte = new_file.read(1)
                if byte:
                    block_data += byte
            else:
                output.append((block_number, len(block_data)))
                block_data = new_file.read(block_size)

        # Now we optimize. This is similar to peep-hole optimization in
        # compilers. We look at adjacent items in output, and if they
        # can be combined (two strings, or adjacent block numbers), we
        # do that.
        
        output2 = []
        while output:
            if type(output[0]) != str:
                block_number, length = output[0]
                offset = block_number * block_size
                
                # Count adjacent blocks at beginning of output.
                i = 1
                while i < len(output):
                    if type(output[i]) == str:
                        break
                    next_block_number, next_length = output[i]
                    next_offset = next_block_number * block_size
                    if next_offset != offset + length:
                        break
                    length += next_length
                    i += 1

                # Now make the OldFileSubString.
                output2.append(obnamlib.OldFileSubString(offset, length))
            else:
                assert type(output[0]) == str
                # Count number of strings at the beginning of output.
                i = 0
                while i < len(output) and type(output[i]) == str:
                    i += 1
                # Now make the FileChunk. Or several: they can only contain
                # up to chunk_size bytes.
                bytes = output[:i]
                while bytes:
                    string = "".join(bytes[:chunk_size])
                    output2.append(obnamlib.FileChunk(string))
                    del bytes[:chunk_size]
            
            # Finally, get rid of prefix from output.
            del output[:i]

        return output2

    def patch(self, output_file, old_file, rsyncdelta): # pragma: no cover
        """Apply rsync delta on old_file, writing output to new_file.
        
        Delta is a list like the one returned by file_delta.
        
        """
        
        for directive in rsyncdelta:
            if directive.kind == obnamlib.FILECHUNK:
                output_file.write(str(directive))
            else:
                assert directive.kind == obnamlib.OLDFILESUBSTRING
                old_file.seek(directive.offset)
                data = old_file.read(directive.length)
                if len(data) != directive.length:
                    raise obnamlib.Exception("Too little data from old file")
                new_file.write(data)

