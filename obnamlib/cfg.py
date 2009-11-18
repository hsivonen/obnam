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
    or false. False is the default. Other options have string values.
    If the app needs a list, it needs to implement it via strings.
    
    FIXME: Everything about reading configuration from files above is
    total bullshit, that part hasn't been implemented yet.
    
    '''
    
    def __init__(self, filenames):
        pass

    def new_boolean(self, names, help):
        pass
        
    def new_string(self, names, help):
        pass

    def __getitem__(self, name):
        return None
        
    def load(self, argv=None):
        pass
