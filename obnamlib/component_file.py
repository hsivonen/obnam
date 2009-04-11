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


class File(obnamlib.CompositeComponent):

    composite_kind = obnamlib.FILE
    
    def __init__(self, filename, stat, contref=None, sigref=None, 
                 deltaref=None, symlink_target=None):
        children = []
        children.append(obnamlib.FileName(filename))
        children.append(obnamlib.Stat(stat))
        if contref is not None:
            children.append(obnamlib.ContRef(contref))
        if sigref is not None:
            children.append(obnamlib.SigRef(sigref))
        if deltaref is not None:
            children.append(obnamlib.DeltaRef(deltaref))
        if symlink_target is not None:
            children.append(obnamlib.SymlinkTarget(symlink_target))
        obnamlib.CompositeComponent.__init__(self, children)

    @property
    def filename(self):
        return self.first_string(kind=obnamlib.FILENAME)

    @property
    def stat(self):
        encoded = self.first_string(kind=obnamlib.STAT)
        return obnamlib.decode_stat(encoded)

    @property
    def contref(self):
        return self.first_string(kind=obnamlib.CONTREF)

    @property
    def sigref(self):
        return self.first_string(kind=obnamlib.SIGREF)

    @property
    def deltaref(self):
        return self.first_string(kind=obnamlib.DELTAREF)

    @property
    def symlink_target(self):
        return self.first_string(kind=obnamlib.SYMLINKTARGET)
