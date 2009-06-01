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


import logging
import subprocess
import zlib

import obnamlib


class BlockTransformation(object):

    """Transform a blob containing a block to a new blob.
    
    Transformations may be chained, and may not assume anything about
    the contents of the blob.
    
    Subclasses must define the to_fs and from_fs methods, and they must
    do a reversible transformation: blob == from_fs(to_fs(blob)) must
    always be true.
    
    """
    
    def configure(self, options):
        """Configure the transformation, assuming it will run."""
    
    def to_fs(self, blob):
        """Transform blob into form that should be written to filesystem."""
        
    def from_fs(self, blob):
        """Undo transformation done by to_fs."""


class GzipTransformation(BlockTransformation):

    def to_fs(self, blob):
        logging.debug("Compressing blob with zlib")
        return zlib.compress(blob)
        
    def from_fs(self, blob):
        logging.debug("Decompressing blob with zlib")
        return zlib.decompress(blob)


class GnuPGTransformation(BlockTransformation):

    def configure(self, options):
        self.encrypt_to = options.encrypt_to
        self.sign_with = options.sign_with
        self.gpg_home = options.gpg_home

    def pipe(self, args, block):
        p = subprocess.Popen(args, stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        stdout, stderr = p.communicate(block)
        if p.returncode != 0: # pragma: no cover
            raise obnamlib.Exception("Subprocess %s failed: %d\n%s" % 
                                     (args, p.returncode, stderr))
        return stdout

    def to_fs(self, blob):
        logging.debug("Encrypting with gpg")
        args = ["gpg"]
        if self.gpg_home:
            args += ["--homedir", self.gpg_home]
        if self.encrypt_to:
            args += ["--encrypt", "--recipient", self.encrypt_to]
        if self.sign_with:
            args += ["--sign", "--local-user", self.sign_with]
        return self.pipe(args, blob)
        
    def from_fs(self, blob):
        logging.debug("Decrypting with gpg")
        args = ["gpg"]
        if self.gpg_home:
            args += ["--homedir", self.gpg_home]
        return self.pipe(args, blob)


block_transformations = [
    GzipTransformation,
    GnuPGTransformation,
]


def choose_transformations(options): # pragma: no cover
    result = []
    if options.use_gzip:
        result.append(GzipTransformation())
    if options.encrypt_to or options.sign_with:
        result.append(GnuPGTransformation())
    for t in result:
        logging.debug("Using transformation %s" % t)
        t.configure(options)
    return result
