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


class SubFilePart(obnamlib.CompositeComponent):

    composite_kind = obnamlib.SUBFILEPART

    def __init__(self, offset, length):
        offset = obnamlib.varint.encode(offset)
        length = obnamlib.varint.encode(length)
        children = [obnamlib.Offset(offset), obnamlib.Length(length)]
        obnamlib.CompositeComponent.__init__(self, children)
        
    def getint(self, kind):
        s = self.first_string(kind=kind)
        return obnamlib.varint.decode(s, 0)[0]
        
    @property
    def offset(self):
        return self.getint(obnamlib.OFFSET)
        
    @property
    def length(self):
        return self.getint(obnamlib.LENGTH)

