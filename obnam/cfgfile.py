# Copyright (C) 2006  Lars Wirzenius <liw@iki.fi>
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


"""Configuration file I/O

This module is similar to Python's standard ConfigParser module, but
can handle options with a list of values. This is important for Obnam,
since some of its options need to be able to be specified multiple 
times. For example, exclude patterns for files.

There seems to be no good way of extending the ConfigParser class,
so this is written from scratch.

"""


import obnam


class Error(obnam.exception.ExceptionBase):

    pass
    
    
class DuplicationError(Error):

    def __init__(self, section):
        self._msg = "section %s already exists" % section


class NoSectionError(Error):

    def __init__(self, section):
        self._msg = "configuration file does not have section %s" % section


class NoOptionError(Error):

    def __init__(self, section, option):
        self._msg = (
            "configuration file does not have option %s in section %s" % 
                (option, section))


class ConfigFile:

    def __init__(self):
        self._dict = {}

    def optionxform(self, option):
        """Transform name of option into canonical form"""
        return option.lower()

    def has_section(self, section):
        """Does this configuration file have a particular section?"""
        return section in self._dict

    def add_section(self, section):
        """Add a new, empty section called section"""
        if self.has_section(section):
            raise DuplicationError(section)
        self._dict[section] = {}

    def parse_string(self, str):
        """Parse a string as a configuration file"""
        pass

    def sections(self):
        """Return all sections we know about"""
        return sorted(self._dict.keys())

    def options(self, section):
        """Return list of option names used in a given section"""
        if not self.has_section(section):
            raise NoSectionError(section)
        return sorted(self._dict[section].keys())

    def has_option(self, section, option):
        """Does a section have a particular option?"""
        if not self.has_section(section):
            raise NoSectionError(section)
        option = self.optionxform(option)
        return option in self._dict[section]

    def set(self, section, option, value):
        """Set the value of an option in a section
        
        Note that this replaces all existing values.
        
        """
        if not self.has_section(section):
            raise NoSectionError(section)
        option = self.optionxform(option)
        self._dict[section][option] = [value]

    def get(self, section, option):
        """Return the value of an option in a section
        
        Note that this can return a string or a list of strings, depending
        on whether the option has a single value, or several. If the option
        has not been set, NoOptionError is raised.
        
        """
        if not self.has_section(section):
            raise NoSectionError(section)
        option = self.optionxform(option)
        if not self.has_option(section, option):
            raise NoOptionError(section, option)
        value = self._dict[section][option]
        if len(value) == 1:
            return value[0]
        else:
            return value

    def getint(self, section, option):
        """Return value of an option in a section as an integer
        
        If the value is not a single string encoding an integer, then
        ValueError is raised.
        
        """
        return int(self.get(section, option), 0)

    def getfloat(self, section, option):
        """Return value of an option in a section as a floating point value
        
        If the value is not a single string encoding a floating point, then
        ValueError is raised.
        
        """
        return float(self.get(section, option))

    def getboolean(self, section, option):
        """Convert value of option in section into a boolean value
        
        The value must be a single string that is "yes", "true", "on", or
        "1" for True (ignoring upper/lowercase), or "no", "false", "off", or
        "0" for False. Any other value will cause ValueError to be raised.
        
        """
        value = self.get(section, option)
        value = value.lower()
        if value in ["yes", "on", "true", "1"]:
            return True
        if value in ["no", "off", "false", "0"]:
            return False
        raise ValueError

    def append(self, section, option, value):
        """Append a new value for an option"""
        if not self.has_section(section):
            raise NoSectionError(section)
        option = self.optionxform(option)
        if self.has_option(section, option):
            self._dict[section][option].append(value)
        else:
            self._dict[section][option] = [value]

    def items(self, section):
        """Return list of (option, value) pairs for a section
        
        Note that the value is a single string, or a list of strings,
        similar to the get method.
        """

        list = []
        for option in self.options(section):
            list.append((option, self.get(section, option)))
        return list
