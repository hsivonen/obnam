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


import heapq
import logging
import os

import obnamlib


#class CounterObjectCache(object):

#    """Cache objects in memory."""
#    
#    # This simulates a clock with a counter: each object is paired with a
#    # value and for each use, the value is set to the current value of the
#    # counter. When it is time to forget, the lowest counter is removed.
#    
#    def __init__(self):
#        self.dict = {}
#        self.counter = 0
#        # Compute a default max cache size by assuming a one megabyte
#        # block size and a 64 byte object size.
#        self.max = 1000 * 1000 / 64
#        
#    def put(self, obj):
#        if obj.id in self.dict:
#            self.dict[obj.id][0] = self.counter
#        else:
#            # We put in a pair as a _list_, not a tuple, so we can 
#            # modify it in place, for speed.
#            self.dict[obj.id] = [self.counter, obj]
#        self.counter += 1
#        self.forget()

#    def forget(self):
#        # We _should_ only be removing one item, but just in case we remove
#        # more, we loop rather than test once. Since this should never
#        # happen, it should be very fast.
#        while len(self.dict) > self.max:
#            keys = self.dict.keys()
#            counters = [(self.dict[objid][0], objid) for objid in keys]
#            counters.sort()
#            del self.dict[counters[0][1]]
#        
#    def get(self, objid):
#        if objid in self.dict:
#            pair = self.dict[objid]
#            pair[0] = self.counter
#            self.counter += 1
#            return pair[1]
#        else:
#            return None


class ComplicatedObjectCache(object):

    """Cache objects in memory."""
    
    # This is an Least-Recently-Used cache for obnam.Objects. Set
    # the `max` attribute to the desired size if the default is not
    # acceptable.
    #
    # We keep track of how long ago an object has been used using
    # a global 'age' counter: whenever an object is used (put or get),
    # we remember the current value of the counter for that object and
    # then increment the counter for the next use.
    #
    # When we need to drop an object from the cache, we find the one
    # with the lowest remembered counter value, and drop that.
    #
    # To keep things speedy, we avoid having to iterate through the 
    # entire set of objects, which may be fairly large. Both get and
    # put methods should be on the order of dict indexing.
    
    def __init__(self):
        self.counter = 0 # counter for age
        self.values = {} # indexed by object id, gives (counter, object)
        self.ages = {}   # indexed by counter, gives object id
        self.smallest = -1 # smallest remembered counter value
        # Compute a default max cache size by assuming a one megabyte
        # block size and a 64 byte object size.
        self.max = 1000 * 1000 / 64

    def get(self, objid):
        pair = self.values.get(objid)
        if pair is None:
            return None
        obj, counter = pair
        self.values[objid] = (obj, self.counter)
        del self.ages[counter]
        self.ages[self.counter] = obj.id
        self.counter += 1
        while self.smallest not in self.ages:
            self.smallest += 1
        return obj
        
    def put(self, obj):
        if obj.id in self.values:
            del self.ages[self.values[obj.id][1]]
            self.values[obj.id] = (obj, self.counter)
            self.ages[self.counter] = obj.id
            self.counter += 1
            while self.smallest not in self.ages:
                self.smallest += 1
        else:
            self.values[obj.id] = (obj, self.counter)
            self.ages[self.counter] = obj.id
            self.counter += 1
            while self.smallest not in self.ages:
                self.smallest += 1
            if len(self.values) > self.max:
                del self.values[self.ages[self.smallest]]
                del self.ages[self.smallest]
                while self.smallest not in self.ages:
                    self.smallest += 1

ObjectCache = ComplicatedObjectCache
