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


class FileGroup(obnamlib.Object):

    """Meta data about a group of files."""

    kind = obnamlib.FILEGROUP

    @property
    def files(self):
        return self.find(kind=obnamlib.FILE)

    @property
    def names(self):
        return [file.first_string(kind=obnamlib.FILENAME)
                for file in self.files]

    def add_file(self, name, stat, contref, sigref, deltaref):
        children = [
            obnamlib.Component(kind=obnamlib.FILENAME, string=name),
            obnamlib.encode_stat(stat),
            obnamlib.Component(kind=obnamlib.CONTREF, string=contref),
            obnamlib.Component(kind=obnamlib.SIGREF, string=sigref),
            obnamlib.Component(kind=obnamlib.DELTAREF, string=deltaref),
        ]
        file = obnamlib.Component(kind=obnamlib.FILE, children=children)
        self.components.append(file)

    def get_file(self, name):
        for file in self.files:
            if file.first_string(kind=obnamlib.FILENAME) == name:
                return (obnamlib.decode_stat(file.first(kind=obnamlib.STAT)),
                        file.first_string(kind=obnamlib.CONTREF),
                        file.first_string(kind=obnamlib.SIGREF),
                        file.first_string(kind=obnamlib.DELTAREF))
        raise obnamlib.NotFound("File %s not found in FileGroup %s" % 
                                (name, self.id))

    def get_stat(self, name):
        return self.get_file(name)[0]
