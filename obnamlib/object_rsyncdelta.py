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


class RsyncDelta(obnamlib.Object):

    """An rsync delta."""

    kind = obnamlib.RSYNCDELTA

    def __init__(self, id, delta_directives=None):
        obnamlib.Object.__init__(self, id)
        if delta_directives:
            self.components += delta_directives
            
    @property
    def delta_directives(self):
        kinds = (obnamlib.FILECHUNK, obnamlib.OLDFILESUBSTRING)
        return [c for c in self.components if c.kind in kinds]
