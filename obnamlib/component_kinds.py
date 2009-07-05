# Copyright (C) 2008  Lars Wirzenius <liw@liw.fi>
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


class ComponentKinds(obnamlib.Kinds):

    """Kinds of Components.

    There are three variants of Component kinds: 

    * plain: just a string value
    * composite: contains other components
    * reference: string value with an object identifier

    The variant is encoded in the lowest two bits of the numeric code:
    0x00 indicates plain, 0x01 indicates composite, and 0x02 indicates
    reference kind. 0x03 is reserved for future expansion: if we need
    more variant bits in the future, we can set the lowest two bits to
    one and the use more bits for flags.

    However, when the caller adds kinds, we don't want to make them
    include the flag bits, so the add_plain, add_composite, and
    add_ref methods take a value shifted down two bits and add the
    bits afterwards. This makes code a bit clearer.

    In all other cases, however, the code is the full code with the
    flag bits.

    """

    MASK = 0x03
    COMPOSITE_FLAG = 0x01
    REF_FLAG = 0x02

    def add_plain(self, code, name):
        """Add a plain kind."""
        self.add(code << 2, name)

    def add_composite(self, code, name):
        """Add a composite kind."""
        self.add((code << 2) | self.COMPOSITE_FLAG, name)

    def add_ref(self, code, name):
        """Add a reference kind."""
        self.add((code << 2) | self.REF_FLAG, name)

    def is_plain(self, code):
        """Is this is a plain kind?"""
        return (code & self.MASK) == 0x00

    def is_composite(self, code):
        """Is this is a composite kind?"""
        return (code & self.MASK) == self.COMPOSITE_FLAG

    def is_ref(self, code):
        """Is this is a reference kind?"""
        return (code & self.MASK) == self.REF_FLAG

    def add_all(self): # pragma: no cover
        """Add all component kinds to ourselves."""

        self.add_plain(     1, "OBJID")
        self.add_plain(     2, "OBJKIND")
        self.add_plain(     3, "BLKID")
        self.add_plain(     4, "FILECHUNK")
        self.add_composite( 5, "OBJECT")
        self.add_composite( 6, "OBJMAP")
        # 7-19 have been obsoleted and should not exist anywhere in the 
        # universe.
        self.add_ref(      20, "CONTREF")
        # now unused: self.add_composite(21, "NAMEIPAIR")
        # 22 has been obsoleted and should not exist anywhere in the universe.
        self.add_plain(    23, "FILENAME")
        self.add_plain(    24, "SIGDATA")
        self.add_ref(      25, "SIGREF")
        self.add_ref(      26, "GENREF")
        # No idea what happened to 27.
        self.add_ref(      28, "OBJREF")
        self.add_ref(      29, "BLOCKREF")
        self.add_ref(      30, "MAPREF")
        self.add_ref(      31, "FILEPARTREF")
        self.add_plain(    32, "FORMATVERSION")
        self.add_composite(33, "FILE")
        self.add_ref(      34, "FILELISTREF")
        self.add_ref(      35, "CONTMAPREF")
        self.add_ref(      36, "DELTAREF")
        self.add_plain(    37, "DELTADATA")
        self.add_plain(    38, "STAT")
        self.add_plain(    39, "GENSTART")
        self.add_plain(    40, "GENEND")
        self.add_ref(      41, "DELTAPARTREF")
        self.add_ref(      42, "DIRREF")
        self.add_ref(      43, "FILEGROUPREF")
        self.add_plain(    44, "SNAPSHOTGEN")
        self.add_plain(    45, "SYMLINKTARGET")
        self.add_plain(    46, "OWNER")
        self.add_plain(    47, "GROUP")
        self.add_composite(48, "CHECKSUMS")
        self.add_plain(    49, "ADLER32")
        self.add_plain(    50, "MD5")
        self.add_plain(    51, "SIGBLOCKSIZE")
        self.add_plain(    52, "OFFSET")
        self.add_plain(    53, "LENGTH")
        self.add_composite(54, "SUBFILEPART")
        self.add_ref(      55, "RSYNCSIGPARTREF")

