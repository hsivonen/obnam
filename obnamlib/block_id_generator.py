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


import uuid

import obnamlib


class BlockIdGenerator(object):

    """Generate new block identifiers for stores.
    
    A block identifier needs to be globally unique. In principle, this
    would mean we could just use UUID4 for them. However, we also need
    to use the block id as a pathname for the file in which the block
    gets stored. Thus we use a differenct scheme, where we generate
    a UUID4 that will be used as the directory name, and N levels of
    numbers to be used as subdirectory and filenames. Thus, given
    a tuple of (UUID4, i1, ..., iN), the full pathname will be
    
        UUID/i1/.../iN
        
    where iN will be the basename of the block file.
    
    Since we don't yet know how many levels of numbers will be
    necessary, we construct the code appropriately. This turns out
    not to add much complexity. We maintain an array of the numbers,
    initialized to all zeroes. When we generate a new id, we increment
    the lowest level number (iN), and when that reaches a maximum,
    we reset it to zero, and increment the higher level (and recursively
    to the top). If the topmost integer reaches maximum, we generate
    a new UUID4 to be used as the top level directory name.

    """
    
    def __init__(self, levels, per_level):
        self.levels = levels
        self.per_level = per_level
        self.counters = [0] * levels
        self.prefix = None

    def generate_prefix(self):
        return str(uuid.uuid4())

    def format_id(self):
        return "/".join([self.prefix] + ["%d" % n for n in self.counters])

    def increment_counters(self, level):
        if self.counters[level] < self.per_level:
            self.counters[level] += 1
        elif level == 0:
            self.prefix = self.generate_prefix()
        else:
            self.counters[level] = 0
            self.increment_counters(level-1)
    
    def new_id(self):
        if self.prefix is None:
            self.prefix = self.generate_prefix()

        id = self.format_id()
        self.increment_counters(self.levels - 1)

        return id
