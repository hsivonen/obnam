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


class SimplisticObjectCache(object):

    """Cache objects in memory."""
    
    # This is a very simplistic LRU implementation: it keeps the objects
    # in a list in the order in which they have last been used.
    
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


class CounterObjectCache(object):

    """Cache objects in memory."""
    
    # This simulates a clock with a counter: each object is paired with a
    # value and for each use, the value is set to the current value of the
    # counter. When it is time to forget, the lowest counter is removed.
    
    def __init__(self):
        self.dict = {}
        self.counter = 0
        # Compute a default max cache size by assuming a one megabyte
        # block size and a 64 byte object size.
        self.max = 1000 * 1000 / 64
        
    def put(self, obj):
        if obj.id in self.dict:
            self.dict[obj.id][0] = self.counter
        else:
            # We put in a pair as a _list_, not a tuple, so we can 
            # modify it in place, for speed.
            self.dict[obj.id] = [self.counter, obj]
        self.counter += 1
        self.forget()

    def forget(self):
        # We _should_ only be removing one item, but just in case we remove
        # more, we loop rather than test once. Since this should never
        # happen, it should be very fast.
        while len(self.dict) > self.max:
            keys = self.dict.keys()
            counters = [(self.dict[objid][0], objid) for objid in keys]
            counters.sort()
            del self.dict[counters[0][1]]
        
    def get(self, objid):
        if objid in self.dict:
            pair = self.dict[objid]
            pair[0] = self.counter
            self.counter += 1
            return pair[1]
        else:
            return None


ObjectCache = CounterObjectCache

