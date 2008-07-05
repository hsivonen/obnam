#!/usr/bin/python
#
# Copyright (C) 2008  Lars Wirzenius <liw@iki.fi>
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


import sys

import obnamlib


def parse_components(data, pos, end):
    while pos < end:
        size, pos = obnamlib.varint.decode(data, pos)
        kind, pos = obnamlib.varint.decode(data, pos)
        yield size, kind, data[pos:pos+size]
        pos += size


def parse_object_kind(data):
    for size, kind, content in parse_components(data, 0, len(data)):
        if kind == obnamlib.cmp.OBJKIND:
            return obnamlib.varint.decode(content, 0)[0]
    return 0 # for unknown


def parse_object_sizes(data):
    assert data.startswith(obnamlib.obj.BLOCK_COOKIE)
    pos = len(obnamlib.obj.BLOCK_COOKIE)
    
    return [(size, parse_object_kind(content))
            for size, kind, content in parse_components(data, pos, len(data))
                if kind == obnamlib.cmp.OBJECT]


for filename in sys.argv[1:]:
    f = file(filename)
    data = f.read()
    f.close()
    for size, objkind in parse_object_sizes(data):
        print size, obnamlib.obj.kind_name(objkind)
