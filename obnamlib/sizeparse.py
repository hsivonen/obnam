# Copyright 2010  Lars Wirzenius
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


import re

import obnamlib


class UnitError(obnamlib.Error):

    def __str__(self):
        return self.msg


class SizeSyntaxError(UnitError):

    def __init__(self, string):
        self.msg = '"%s" is not a valid size' % string


class UnitNameError(UnitError):

    def __init__(self, string):
        self.msg = '"%s" is not a valid unit' % string


class ByteSizeParser(object):

    '''Parse sizes of data in bytes, kilobytes, kibibytes, etc.'''
    
    pat = re.compile(r'^(?P<size>\d+(\.\d+)?)\s*'
                     r'(?P<unit>[kmg]?i?b?)?$', re.I)
    
    units = {
        'b': 1,
        'k': 1000,
        'kb': 1000,
        'kib': 1024,
        'm': 1000**2,
        'mb': 1000**2,
        'mib': 1024**2,
        'g': 1000**3,
        'gb': 1000**3,
        'gib': 1024**3,
    }
    
    def __init__(self):
        self.set_default_unit('B')
        
    def set_default_unit(self, unit):
        if unit.lower() not in self.units:
            raise UnitNameError(unit)
        self.default_unit = unit
        
    def parse(self, string):
        m = self.pat.match(string)
        if not m:
            raise SizeSyntaxError(string)
        size = float(m.group('size'))
        unit = m.group('unit')
        if not unit:
            unit = self.default_unit
        elif unit.lower() not in self.units:
            raise UnitNameError(unit)
        factor = self.units[unit.lower()]
        return int(size * factor)

