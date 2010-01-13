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
import os

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


def require_host_lock(method):
    '''Decorator for ensuring the currently open host is locked by us.'''
    
    def helper(self, *args, **kwargs):
        if not self.got_host_lock:
            raise LockFail('have not got lock on host')
        return method(self, *args, **kwargs)
    
    return helper


def require_open_host(method):
    '''Decorator for ensuring store has an open host.
    
    Host may be read/write (locked) or read-only.
    
    '''
    
    def helper(self, *args, **kwargs):
        if self.current_host is None:
            raise obnamlib.Error('host is not open')
        return method(self, *args, **kwargs)
    
    return helper


class Store(object):

    '''Store backup data.
    
    Backup data is stored on a virtual file system
    (obnamlib.VirtualFileSystem instance), in some form that
    the API of this class does not care about.
    
    The store may contain data for several hosts that share 
    encryption keys. Each host is identified by a name.
    
    The store has a "root" object, which is conceptually a list of
    host names.
    
    Each host in turn is conceptually a list of generations,
    which correspond to snapshots of the user data that existed
    when the generation was created.
    
    Read-only access to the store does not require locking.
    Write access may affect only the root object, or only a host's
    own data, and thus locking may affect only the root, or only
    the host.
    
    When a new generation is started, it is a copy-on-write clone
    of the previous generation, and the caller needs to modify
    the new generation to match the current state of user data.

    '''

    def __init__(self, fs):
        self.fs = fs
        self.got_root_lock = False
        self.got_host_lock = False
        self.host_lockfile = None
        self.current_host = None
        self.new_generation = None
        
    def list_hosts(self):
        '''Return list of names of hosts using this store.'''
        return [x for x in self.fs.listdir('.') if self.fs.isdir(x)]

    def lock_root(self):
        '''Lock root node.
        
        Raise obnamlib.LockFail if locking fails. Lock will be released
        by commit_root() or unlock_root().
        
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
        
    @require_root_lock
    def remove_host(self, hostname):
        '''Remove a host from the store.
        
        This removes all data related to the host, including all
        actual file data unless other hosts also use it.
        
        '''
        
        if not self.fs.isdir(hostname):
            raise obnamlib.Error('host %s does not exist' % hostname)
        self.fs.rmtree(hostname)
        
    def lock_host(self, hostname):
        '''Lock a host for exclusive write access.
        
        Raise obnamlib.LockFail if locking fails. Lock will be released
        by commit_host() or unlock_host().

        '''
        
        lockname = os.path.join(hostname, 'lock')
        try:
            self.fs.write_file(lockname, '')
        except OSError, e:
            if e.errno == errno.EEXIST:
                raise LockFail('Host %s is already locked' % hostname)
        self.got_host_lock = True
        self.host_lockfile = lockname
        self.current_host = hostname

    @require_host_lock
    def unlock_host(self):
        '''Unlock currently locked host.'''
        self.fs.remove(self.host_lockfile)
        self.host_lockfile = None
        self.got_host_lock = False
        self.current_host = None

    @require_host_lock
    def commit_host(self):
        '''Commit changes to and unlock currently locked host.'''
        self.unlock_host()
        
    def open_host(self, hostname):
        '''Open a host for read-only operation.'''
        self.current_host = hostname
        
    @require_open_host
    def list_generations(self):
        '''List existing generations for currently open host.'''
        return []
        
    @require_host_lock
    def start_generation(self):
        '''Start a new generation.'''
        if self.new_generation is not None:
            raise obnamlib.Error('Cannot start two new generations')
        self.new_generation = 'static.id.for.now'
