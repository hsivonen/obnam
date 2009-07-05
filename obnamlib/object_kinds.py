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


class ObjectKinds(obnamlib.Kinds):

    """Kinds of Objects."""

    def add_all(self): # pragma: no cover
        """Add all object kinds to ourselves."""
        self.add( 1, "FILEPART")
        # object kind 2 used to be INODE, but it's been removed
        self.add( 3, "GEN")
        self.add( 4, "SIG")
        self.add( 5, "HOST")
        self.add( 6, "FILECONTENTS")
        self.add( 7, "FILELIST")
        self.add( 8, "DELTA")
        self.add( 9, "DELTAPART")
        self.add(10, "DIR")
        self.add(11, "FILEGROUP")
        self.add(12, "RSYNCSIGPART")
        self.add(13, "RSYNCDELTA")

