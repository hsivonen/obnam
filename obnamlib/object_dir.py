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


class Dir(obnamlib.Object):

    """Meta data about a directory."""

    kind = obnamlib.DIR

    def __init__(self, id, name=None, dirrefs=None, fgrefs=None):
        obnamlib.Object.__init__(self, id=id)

        self.name = name
        self.dirrefs = dirrefs or []
        self.fgrefs = fgrefs or []

    def add_refs(self, kind, refs):
        self.components += [obnamlib.Component(kind=kind, string=ref)
                            for ref in refs]

    def prepare_for_encoding(self):
        c = obnamlib.Component(kind=obnamlib.FILENAME, string=self.name)
        self.components.append(c)
        self.add_refs(obnamlib.DIRREF, self.dirrefs)
        self.add_refs(obnamlib.FILEGROUPREF, self.fgrefs)
