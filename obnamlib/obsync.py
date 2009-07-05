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
import StringIO
import zlib


"""A pure-Python implementation of the rsync algorithm.

See http://www.samba.org/rsync/tech_report/ for an explanation of the
rsync algorithm.

This is not at all compatible with rsync the program, or rdiff, or
librsync, or any other implementation of the rsync algorithm. It does not
even implement the algorithm as described in the original paper. This
is mostly because a) Python sucks as bit twiddling kinds of things, so
we have chosen approaches that are fast in Python, and b) this is meant
to be part of Obnam, a backup program, which changes the requirements of
generic rsync a little bit.

"""
    

    
def weak_checksum(data):
    """Compute weak checksum for data.
    
    Return obnamlib.Adler32 component.
    
    """
    
    return obnamlib.Adler32(str(zlib.adler32(data)))


def strong_checksum(data):
    """Compute weak checksum for data.
    
    Return obnamlib.Md5 component.
    
    """

    return obnamlib.Md5(hashlib.md5(data).digest())


class RsyncSignatureGenerator(object):

    """Generate the rsync signature."""

    def __init__(self):
        self.buf = ""

    def block_signature(self, block_data):
        """Compute rsync signature for a given block of data.
        
        Return an obnamlib.Checksums component.
        
        Assume the block is of whatever size the signatures should be
        computed for. It is the caller's responsibility to make sure
        all blocks in a signature file are of the same size.
        
        """
        
        weak = weak_checksum(block_data)
        strong = strong_checksum(block_data)
        return obnamlib.Checksums([weak, strong])
        
    def buffered_block_signature(self, new_data, block_size): # pragma: no cover
        """Compute rsync signature from a sequence of data.
        
        This method is meant to be called a number of times. Each time,
        some more data is provided. Whenever there's enough data, rsync
        signatures for additional blocks are computed. Each call returns
        the list of new signatures. The final call must provide
        an empty string as new_data, at which point the internal buffer
        is cleared and all remaining signatures are returned.
        
        """
        
        self.buf += new_data
        
        sigs = []
        while len(self.buf) >= block_size:
            sigs.append(self.block_signature(self.buf[:block_size]))
            self.buf = self.buf[block_size:]

        if not new_data:
            sigs.append(self.block_signature(self.buf))
            self.buf = ""

        return sigs

    def file_signature(self, f, block_size):
        """Compute signatures for a file.
        
        Generate a list of obnamlib.Checksums objects.
        
        """
        
        while True:
            block = f.read(block_size)
            if not block:
                break
            yield self.block_signature(block)


class RsyncLookupTable(object):

    """Look up matching blocks from a signature file."""

    def __init__(self, compute_weak=None, compute_strong=None):
        self.compute_weak = compute_weak or weak_checksum
        self.compute_strong = compute_strong or strong_checksum
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


class RsyncDeltaGenerator(object):

    """Generate a delta from signature file and new version of a file."""

    def simple_file_delta(self, rsyncsigparts, new_file, chunk_size):
        """Compute an unoptimized delta from signature file to new file.
        
        Generate a sequence of single-byte strings and tuples of
        block number and length in the old file. This makes no
        attempt at combining adjacent bytes to a single string,
        or otherwise optimizing the result.
        
        """

        block_size = rsyncsigparts[0].block_size
        lookup_table = RsyncLookupTable()
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
                yield block_data[0]
                block_data = block_data[1:]
                byte = new_file.read(1)
                if byte:
                    block_data += byte
            else:
                yield (block_number * block_size, len(block_data))
                block_data = new_file.read(block_size)

    def file_delta(self, rsyncsigparts, new_file, chunk_size):
        """Compute delta from RsyncSigParts to new_file.
        
        Generate obnamlib.FileChunk and obnamlib.OldFileSubString objects.
        
        """

        # Now we optimize. This is similar to peep-hole optimization in
        # compilers. We look at adjacent items in output, and if they
        # can be combined (two strings, or adjacent blocks), we do that.
        
        # We'll keep all un-yielded items in a queue. The queue will contain
        # either a sequence of single-byte strings or a single tuple.
        # The strings will be combined into one when we generate a
        # FileChunk. This way we only catenate the strings once, which
        # is potentially a big performance win.
        queue = []

        for x in self.simple_file_delta(rsyncsigparts, new_file, chunk_size):
            if not queue:
                queue = [x]
            elif type(queue[0]) == str:
                if type(x) == str:
                    queue.append(x)
                else:
                    yield obnamlib.FileChunk(''.join(queue))
                    queue = [x]
            else:
                offset, length = queue[0]
                if type(x) == tuple:
                    new_offset, new_length = x
                    if new_offset == offset + length:
                        queue = [(offset, length + new_length)]
                    else:
                        yield obnamlib.OldFileSubString(offset, length)
                        queue = [x]
                else:
                    yield obnamlib.OldFileSubString(offset, length)
                    queue = [x]
        if queue:
            if type(queue[0]) == str:
                yield obnamlib.FileChunk(''.join(queue))
            else:
                offset, length = queue[0]
                yield obnamlib.OldFileSubString(offset, length)


class RsyncPatcher(object):

    """Apply delta from RsyncDeltaGenerator against old version of file."""

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

