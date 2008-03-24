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

The way it works: 

    foo = bar
    # foo now has one value, "bar"
    foo += foobar
    # note the +=; foo now has two values, "bar" and "foobar"
    foo = pink
    # foo now has one value again, "pink"

This also works across configuration files.

This module does not support the interpolation or defaults features
of ConfigParser. It should otherwise be compatible.

"""


import re

import obnam


class Error(obnam.ObnamException):

    pass
    
    
class DuplicationError(Error):

    def __init__(self, section):
        self._msg = "section %s already exists" % section


class NoSectionError(Error):

    def __init__(self, section):
        self._msg = "configuration file does not have section %s" % section


class NoOptionError(Error):

    def __init__(self, section, option):
        self._msg = ("configuration file does not have option %s "
                     "in section %s" % (option, section))


class ParsingError(Error):
    
    def __init__(self, filename, lineno):
        if filename is None:
            self._msg = "Syntax error on line %d of unnamed file" % lineno
        else:
            self._msg = "Syntax error in %s, line %d" % (filename, lineno)


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
        value = value.lower().strip()
        if value in ["yes", "on", "true", "1"]:
            return True
        if value in ["no", "off", "false", "0"]:
            return False
        raise ValueError

    def getvalues(self, section, option):
        """Return list of values for an option in a section
        
        Note that the return value is always a list of strings. It might
        be empty.
        
        """
        values = self.get(section, option)
        if values == "":
            return []
        if type(values) != type([]):
            values = [values]
        return values

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

    def remove_option(self, section, option):
        """Remove an option (all values) from a section"""
        if not self.has_section(section):
            raise NoSectionError(section)
        option = self.optionxform(option)
        if self.has_option(section, option):
            del self._dict[section][option]
            return True
        else:
            return False

    def remove_section(self, section):
        """Remove a section"""
        if self.has_section(section):
            del self._dict[section]
            return True
        else:
            return False

    def write(self, f):
        """Write configuration file to open file"""
        for section in self.sections():
            f.write("[%s]\n" % section)
            for option in self.options(section):
                values = self.get(section, option)
                if type(values) != type([]):
                    f.write("%s = %s\n" % (option, values))
                else:
                    if values:
                        f.write("%s = %s\n" % (option, values[0]))
                    for value in values[1:]:
                        f.write("%s += %s\n" % (option, value))

    # Regular expression patterns for parsing configuration files.
    comment_pattern = re.compile(r"\s*(#.*)?$")
    section_pattern = re.compile(r"\[(?P<section>.*)\]$")
    option_line1_pattern = re.compile(r"(?P<option>\S*)\s*(?P<op>\+?=)" +
                                      r"(?P<value>.*)$")
    option_line2_pattern = re.compile(r"\s+(?P<value>.*)$")

    def handle_section(self, section, option, match):
        section = match.group("section")
        if not self.has_section(section):
            # It's OK for the section to exist already. We might be reading
            # several configuration files into the same CfgFile object.
            self.add_section(section)
        return section, option
        
    def handle_option_line1(self, section, option, match):
        option = match.group("option")
        op = match.group("op")
        value = match.group("value")
        value = value.strip()
        if op == "+=":
            self.append(section, option, value)
        else:
            self.set(section, option, value)
        return section, option
        
    def handle_option_line2(self, section, option, match):
        value = match.group("value")

        values = self.get(section, option)
        if type(values) != type([]):
            values = [values]
        if values:
            values[-1] = values[-1] + " " + value.strip()

        self.remove_option(section, option)
        for value in values:
            self.append(section, option, value)

        return section, option

    def handle_comment(self, section, option, match):
        return section, option

    def readfp(self, f, filename=None):
        """Read configuration file from open file"""
        filename = filename or getattr(f, "filename", None)

        lineno = 0
        section = None
        option = None

        matchers = ((self.comment_pattern, self.handle_comment),
                    (self.section_pattern, self.handle_section),
                    (self.option_line1_pattern, self.handle_option_line1),
                    (self.option_line2_pattern, self.handle_option_line2),
                   )
    
        while True:
            line = f.readline()
            if not line:
                break
            lineno += 1

            m = None
            for pattern, func in matchers:
                m = pattern.match(line)
                if m:
                    section, option = func(section, option, m)
                    break
            if not m:
                raise ParsingError(filename, lineno)
