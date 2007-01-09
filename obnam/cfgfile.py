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


class ConfigFile:

    def parse_string(self, str):
        """Parse a string as a configuration file"""
        pass

    def sections(self):
        """Return all sections we know about"""
        return []
