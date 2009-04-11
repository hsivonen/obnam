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


class Symlink(obnamlib.CompositeComponent):

    composite_kind = obnamlib.SYMLINK
    
    def __init__(self, filename, stat, target):
        children = []
        if filename is not None:
            children.append(obnamlib.FileName(filename))
        if stat is not None:
            children.append(obnamlib.Stat(stat))
        if target is not None:
            children.append(obnamlib.SymlinkTarget(target))
        obnamlib.CompositeComponent.__init__(self, children)

    @property
    def filename(self):
        return self.first_string(kind=obnamlib.FILENAME)

    @property
    def stat(self):
        encoded = self.first_string(kind=obnamlib.STAT)
        if encoded:
            return obnamlib.decode_stat(encoded)
        else:
            return None

    @property
    def target(self):
        return self.first_string(kind=obnamlib.SYMLINKTARGET)
