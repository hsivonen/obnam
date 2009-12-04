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


import obnamlib


TYPE_ID = 'id'
TYPE_ID_LIST = 'id-list'
TYPE_INT = 'int'
TYPE_STR = 'str'


class BackupObject(object):

    '''An object in the backup store.
    
    A backup object contains some fields, which may be accessed as attributes.
    For example, the obj.id field is the unique identifier of the object.
    
    Fields are defined by the attribute fields, which must be a list of
    (name, type) pairs. Type is one of obnamlib.TYPE_ID, 
    obnamlib.TYPE_ID_LIST, obnamlib.TYPE_INT, obnamlib.TYPE_STR.
    
    The identifier is unique within the backup store, and assigned by the
    store. Until we put the object into the store, it has no id. After
    we put the object into the store, it cannot be modified.
    
    '''

    def __init__(self, **kwargs):
        self.__dict__['values'] = dict()
        for name, kind in self.fields:
            self.values[name] = (kind, None)
        self.values['id'] = (TYPE_ID, None)
        self.set_from_kwargs(**kwargs)

    def set_from_kwargs(self, **kwargs):
        for name, value in kwargs.iteritems():
            setattr(self, name, value)
    
    def __getattr__(self, name):
        if name in self.values:
            kind, value = self.values[name]
            return value
        else:
            raise AttributeError(name)

    types = {
        TYPE_ID: (int, None),
        TYPE_ID_LIST: (list, int),
        TYPE_INT: (int, None),
        TYPE_STR: (str, None),
    }

    def compatible(self, kind, value):
        if kind in self.types:
            main, sub = self.types[kind]
            return (type(value) == main and
                    (sub is None or
                     [sub]*len(value) == [type(x) for x in value]))
        else: # pragma: no cover
            raise Exception('Unknown BackupObject field type %s' % kind)

    def __setattr__(self, name, value):
        if name in self.values:
            kind, old_value = self.values[name]
            if value is None or self.compatible(kind, value):
                self.values[name] = (kind, value)
            else:
                raise TypeError('%s must have value of type %s' % 
                                (name, kind))
        else:
            raise Exception('Cannot set unknown field %s' % name)

    def fieldnames(self):
        return self.values.keys()


class MetadataObject(BackupObject):

    '''Like BackupObject, but adds file/directory metadata fields.
    
    Fields for stat(2) fields are added to the object automatically.
    
    '''
    
    def __init__(self, **kwargs):
        BackupObject.__init__(self)
        for field in obnamlib.metadata_fields:
            if field.startswith('st_'):
                self.values[field] = (TYPE_INT, None)
        self.values['username'] = (TYPE_STR, None)
        self.values['groupname'] = (TYPE_STR, None)
        if 'metadata' in kwargs:
            self.set_from_metadata(kwargs['metadata'])
            del kwargs['metadata']
        self.set_from_kwargs(**kwargs)

    def set_from_metadata(self, metadata):
        for field in obnamlib.metadata_fields:
            kind, old_value = self.values[field]
            value = getattr(metadata, field)
            if value is not None:
                value = self.convert(kind, value)
            setattr(self, field, value)

    def convert(self, kind, value):
        if kind in self.types:
            main, sub = self.types[kind]
            return main(value)
        else: # pragma: no cover
            raise Exception('Unknown BackupObject field type %s' % kind)

