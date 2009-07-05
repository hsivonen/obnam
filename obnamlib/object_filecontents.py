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


class FileContents(obnamlib.Object):

    """Store the full contents of a file."""

    kind = obnamlib.FILECONTENTS

    def __init__(self, id):
        obnamlib.Object.__init__(self, id=id)

    @property
    def part_ids(self):
        return self.find_strings(kind=obnamlib.FILEPARTREF)

    def get_md5(self): # pragma: no cover
        strings = self.find_strings(kind=obnamlib.MD5)
        if strings:
            return strings[0]
        else:
            return None

    def set_md5(self, value): # pragma: no cover
        self.extract(kind=obnamlib.MD5)
        self.components += [obnamlib.Md5(value)]
        
    md5 = property(get_md5, set_md5)

    def add(self, ref):
        c = obnamlib.FilePartRef(ref)
        self.components.append(c)
        
    def add_rsyncsigpartref(self, ref): # pragma: no cover
        c = obnamlib.RsyncSigPartRef(ref)
        self.components.append(c)

    def get_rsyncsigpartrefs(self): # pragma: no cover
        return self.find_strings(kind=obnamlib.RSYNCSIGPARTREF)

    def set_rsyncsigpartrefs(self, new_refs): # pragma: no cover
        self.extract(kind=obnamlib.RSYNCSIGPARTREF)
        self.components += [obnamlib.RsyncSigPartRef(x) for x in new_refs]
        
    rsyncsigpartrefs = property(get_rsyncsigpartrefs, set_rsyncsigpartrefs)

