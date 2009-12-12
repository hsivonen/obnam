# Copyright (C) 2009  Lars Wirzenius
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


import inspect
import pickle

import obnamlib
import obnamlib.objs


class ObjectCodec(object):

    '''Encode/decode BackupObject instances for persistent storage.'''
    
    def __init__(self):
        names = dir(obnamlib.objs)
        things = [getattr(obnamlib.objs, x) for x in names]
        classes = [x 
                   for x in things 
                   if type(x) == type(obnamlib.BackupObject) and
                      x.__module__ == 'obnamlib.objs']
        self.typemap = dict()
        for klass in classes:
            self.typemap[klass.__name__] = klass
            
    def encode(self, obj):
        fields = dict([(x, getattr(obj, x)) for x in obj.fieldnames()])
        fields[':type:'] = obj.__class__.__name__
        return pickle.dumps(fields)
            
    def decode(self, encoded):
        fields = pickle.loads(encoded)
        klass = self.typemap[fields[':type:']]
        del fields[':type:']
        return klass(**fields)


class Store(object):

    '''Persistent storage of backup objects.'''
    
    # In this silly implementation we store each object in its own file,
    # named after it object id (with '.obj' suffix). We use the 
    # ObjectCodec class to convert the backup objects between Python
    # objects and a string representation.
    #
    # We also keep track of the latest object id we've assigned.

    def __init__(self, fs):
        self.fs = fs
        self.codec = ObjectCodec()
        self.latest_id = self.read_latest_id()

    def commit(self):
        self.save_latest_id()

    def read_latest_id(self):
        if self.fs.exists('latest-id'):
            return int(self.fs.cat('latest-id'))
        else:
            return 0
        
    def save_latest_id(self):
        self.fs.overwrite_file('latest-id', '%d' % self.latest_id)

    def next_id(self):
        self.latest_id += 1
        return self.latest_id

    def put_object(self, obj):
        if isinstance(obj, obnamlib.Root):
            assert obj.id == 0, 'root object must have id 0'
        else:
            assert obj.id is None
        if obj.id is None:
            obj.id = self.next_id()
        encoded = self.codec.encode(obj)
        self.fs.write_file('%s.obj' % obj.id, encoded)

    def get_object(self, objid):
        encoded = self.fs.cat('%s.obj' % objid)
        return self.codec.decode(encoded)

