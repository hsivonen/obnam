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


import copy
import optparse

import obnamlib


class Setting(object):

    '''One setting.
    
    We don't use basic types to store settings so that we can more
    easily have aliases for their names.
    
    '''
    
    def __init__(self, kind, value):
        self.kind = kind
        self.value = value


class Configuration(object):

    '''Handle configuration for the application.
    
    The configuration is loaded from a set of configuration files, and 
    the command line. The settings are combined: if something is set
    in the first configuration file, but not the second, it stays set.
    If the second file sets the value to something else, that value
    is used.
    
    Every setting is available via configuration files, and the command
    line.
    
    In addition to command line options, we store the non-option command
    line arguments as well (attribute `args`).
    
    Configuration files are in ConfigParser format. All settings are in
    the same section, called '[config]'.
    
    The Configuration object acts as a dictionary: cfg['foo'] is the
    setting foo. It can be changed as well as read, but there is no
    way to write changed settings to permanent storage.
    
    Normal long options are boolean settings: the value is either true
    or false. False is the default. Other options have string values, or
    are lists of strings. A list is given either as multiple command
    line options ('--foo=bar --foo=foobar' would result in the
    list ['bar', 'foobar']), or as a comma-and-maybe-also-space separated list
    ('--foo=bar,foobar').
    
    FIXME: Everything about reading configuration from files above is
    total bullshit, that part hasn't been implemented yet.
    
    '''
    
    def __init__(self, filenames):
        self.settings = {}
        self.parser = optparse.OptionParser()
        self.args = []

    def new_setting(self, kind, names, help, action, value):
        setting = Setting(kind, copy.copy(value))
        for name in names:
            self.settings[name] = setting

        optnames = ['-%s' % name for name in names if len(name) == 1]
        optnames += ['--%s' % name for name in names if len(name) > 1]
        self.parser.add_option(*optnames, action=action, help=help,
                               default=copy.copy(value))

    def new_boolean(self, names, help):
        self.new_setting('int', names, help, 'store_true', False)
        
    def new_string(self, names, help):
        self.new_setting('str', names, help, 'store', '')

    def new_list(self, names, help):
        self.new_setting('list', names, help, 'append', [])

    def make_attribute_name(self, name):
        return '_'.join(name.split('-'))

    def __getitem__(self, name):
        return self.settings[name].value

    def __setitem__(self, name, value):
        self.settings[name].value = value
        self.parser.set_default(self.make_attribute_name(name), value)
        
    def load(self, args=None):
        opts, self.args = self.parser.parse_args(args=args)
        for name in self.settings.keys():
            attr = self.make_attribute_name(name)
            if hasattr(opts, attr):
                value = getattr(opts, attr)
                if self.settings[name].kind == 'list':
                    for item in value:
                        item = [s.strip() for s in item.split(',')]
                        self.settings[name].value += item
                else:
                    self.settings[name].value = value

    def require(self, name):
        '''Make sure the named option is set.'''
        
        if not self[name]:
            raise obnamlib.Error('you must use option --%s' % name)
