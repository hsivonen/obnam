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
    def symlinks(self):
        return self.find(kind=obnamlib.SYMLINK)

    @property
    def names(self):
        return [x.filename for x in self.files + self.symlinks]

    def add_file(self, name, stat, contref, sigref, deltaref):
        file = obnamlib.File(name, stat, contref, sigref, deltaref)
        self.components.append(file)

    def add_symlink(self, name, stat, target):
        symlink = obnamlib.Symlink(name, stat, target)
        self.components.append(symlink)

    def get_file(self, name):
        for file in self.files:
            if file.filename == name:
                return (file.stat, file.contref, file.sigref, file.deltaref)
        raise obnamlib.NotFound("File %s not found in FileGroup %s" % 
                                (name, self.id))

    def get_symlink(self, name):
        for symlink in self.symlinks:
            if symlink.filename == name:
                return (symlink.stat, symlink.target)
        raise obnamlib.NotFound("Symlink %s not found in FileGroup %s" % 
                                (name, self.id))

    def get_stat(self, name):
        for x in self.files + self.symlinks:
            if x.filename == name:
                return x.stat
        raise obnamlib.NotFound("File or symlink %s not found in FileGroup %s"
                                % (name, self.id))
