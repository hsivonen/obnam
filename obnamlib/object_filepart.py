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


class FilePart(obnamlib.Object):

    """Store part of a content of a file.

    A file may be arbitrarily big, but objects must fit into blocks,
    so we split a file into suitably sized parts. This class stores
    one such part.

    """

    def __init__(self, id, data):
        obnamlib.Object.__init__(self, kind=obnamlib.FILEPART, id=id)
        self.data = data

    def get_data(self):
        """Return the contents of this FILEPART."""
        return self.find(kind=obnamlib.FILECHUNK)[0].string

    def set_data(self, data):
        self.extract(kind=obnamlib.FILECHUNK)
        c = obnamlib.Component(kind=obnamlib.FILECHUNK)
        c.string = data
        self.components.append(c)

    data = property(get_data, set_data)
