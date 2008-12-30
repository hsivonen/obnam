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


class Mapping(dict):

    """Store mappings from object to block identifiers.
    
    This is otherwise like a plain dictionary, but it keeps only one
    copy of each value. This is useful since a single block typically
    contains a large number of objects, so there are a lot of object
    identifiers pointing at the same block identifier.
    
    """

    def __init__(self):
        dict.__init__(self)
        
        # We keep track of the values in an auxiliary dictionary. We
        # don't use the built-in intern function on the values, since a)
        # during unit testing, they might not be strings (but mock
        # objects), and b) we want to reclaim memory from the interning,
        # which isn't doable with intern. By keeping them in a separate
        # dict, both problems are solved. Memory is reclaimed when
        # the Mapping instance is destroyed.
        self.interned = {}
        
    def __setitem__(self, key, value):
        if value not in self.interned:
            self.interned[value] = value
        value = self.interned[value]
        dict.__setitem__(self, key, value)
