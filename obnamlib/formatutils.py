# Copyright (C) 2009  Lars Wirzenius <liw@liw.fi>
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


size_units = [
    (1000**3, "GB"),
    (1000**2, "MB"),
    (1000, "kB"),
    (0, "B"), # Last item MUST be zero!
]

def format_size(size):
    """Format a file size into bytes, kilobytes, megabytes, etc."""
    for factor, unit in size_units:
        if size >= factor:
            if factor > 0:
                count = int(round(float(size) / factor))
            else:
                count = size
            return "%s %s" % (count, unit)


time_units = [
    (24*60*60, "d"),
    (60*60, "h"),
    (60, "min"),
    (0, "s"),
]      
            
def format_time(seconds):
    """Format a length of time into human-readable form."""
    
    parts = []
    for factor, unit in time_units:
        if seconds >= factor and factor > 0:
            n = seconds / factor
            seconds -= n * factor
            parts.append("%s %s" % (n, unit))
        elif factor == 0 and (seconds > 0 or not parts):
            parts.append("%s %s" % (seconds, unit))
    
    return " ".join(parts)
