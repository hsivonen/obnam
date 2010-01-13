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


import obnamlib


class LockFail(Exception):

    pass


class Store(object):

    def __init__(self, fs):
        self.fs = fs
        
    def list_hosts(self):
        '''Return list of names of hosts using this store.'''
        return []

    def lock_root(self):
        '''Lock root node.
        
        Raise obnamlib.LockFail if locking fails. Lock will be released
        by commit() or unlock_root().
        
        '''

    def unlock_root(self):
        '''Unlock root node without committing changes made.'''
        
    def commit_root(self):
        '''Commit changes to root node, and unlock it.'''

