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


class BlockTransformation(object):

    """Transform a blob containing a block to a new blob.
    
    Transformations may be chained, and may not assume anything about
    the contents of the blob.
    
    Subclasses must define the to_fs and from_fs methods, and they must
    do a reversible transformation: blob == from_fs(to_fs(blob)) must
    always be true.
    
    """
    
    def to_fs(self, blob):
        """Transform blob into form that should be written to filesystem."""
        
    def from_fs(self, blob):
        """Undo transformation done by to_fs."""


class GzipTransform(BlockTransformation):

    def to_fs(self, blob):
        return blob
        
    def from_fs(self, blob):
        return blob


block_transformations = [
    GzipTransform,
]
