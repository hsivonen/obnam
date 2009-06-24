# Copyright (C) 2008, 2009  Lars Wirzenius <liw@liw.fi>
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


import logging
import os

import obnamlib


class ObjectCache(object):

    """Cache objects in memory."""
    
    def __init__(self):
        self.dict = {}
        self.order = []
        # Compute a default max cache size by assuming a one megabyte
        # block size and a 64 byte object size.
        self.max = 1000 * 1000 / 64
        
    def put(self, obj):
        self.dict[obj.id] = obj
        self.use(obj.id)
        self.forget()

    def use(self, objid):
        if objid in self.order:
            self.order.remove(objid)
        self.order.append(objid)

    def forget(self):
        while len(self.order) > self.max:
            del self.dict[self.order[0]]
            del self.order[0]
        
    def get(self, objid):
        if objid in self.dict:
            self.use(objid)
            return self.dict[objid]
        else:
            return None

