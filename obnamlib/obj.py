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

    def compatible(self, kind, value):
        if kind == TYPE_ID:
            return type(value) == int
        elif kind == TYPE_ID_LIST:
            if type(value) != list:
                return False
            for item in value:
                if type(item) != int:
                    return False
            return True
        elif kind == TYPE_INT:
            return type(value) == int
        elif kind == TYPE_STR:
            return type(value) == str
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


class MetadataObject(BackupObject):

    '''Like BackupObject, but adds file/directory metadata fields.
    
    Fields for stat(2) fields are added to the object automatically.
    
    '''
    
    def __init__(self, **kwargs):
        BackupObject.__init__(self)
        stat_fields = ('st_mtime',)
        for stat_field in stat_fields:
            self.values[stat_field] = (TYPE_INT, None)
        self.set_from_kwargs(**kwargs)

