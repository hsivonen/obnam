# Copyright (C) 2009, 2010  Lars Wirzenius
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


# NOTE: THIS IS EXTREMELY NOT INTENDED TO BE PRODUCTION READY. THIS
# WHOLE MODULE EXISTS ONLY TO PLAY WITH THE INTERFACE. THE IMPLEMENTATION
# IS TOTALLY STUPID.


import errno

import obnamlib


class LockFail(Exception):

    pass


def require_root_lock(method):
    '''Decorator for ensuring the store's root node is locked.'''
    
    def helper(self, *args, **kwargs):
        if not self.got_root_lock:
            raise LockFail('have not got lock on root node')
        return method(self, *args, **kwargs)
    
    return helper


class Store(object):

    def __init__(self, fs):
        self.fs = fs
        self.got_root_lock = False
        
    def list_hosts(self):
        '''Return list of names of hosts using this store.'''
        return []

    def lock_root(self):
        '''Lock root node.
        
        Raise obnamlib.LockFail if locking fails. Lock will be released
        by commit() or unlock_root().
        
        '''
        
        try:
            self.fs.write_file('root.lock', '')
        except OSError, e:
            if e.errno == errno.EEXIST:
                raise LockFail('Lock file root.lock already exists')
        self.got_root_lock = True

    @require_root_lock
    def unlock_root(self):
        '''Unlock root node without committing changes made.'''
        self.fs.remove('root.lock')
        self.got_root_lock = False
        
    @require_root_lock
    def commit_root(self):
        '''Commit changes to root node, and unlock it.'''
        self.unlock_root()
        
    @require_root_lock
    def add_host(self, hostname):
        '''Add a new host to the store.'''
        if self.fs.exists(hostname):
            raise obnamlib.Error('host %s already exists in store' % hostname)
        self.fs.mkdir(hostname)
