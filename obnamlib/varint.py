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


"""Variable length integers"""


def encode(i):
    """Encode an integer as a varint"""
    return "%d\n" % i


def decode(encoded, pos):
    """Decode a varint from a string, return value and pos after it"""
    i = encoded.find("\n", pos)
    if i == -1:
        return -1, pos
    else:
        return int(encoded[pos:i]), i+1
