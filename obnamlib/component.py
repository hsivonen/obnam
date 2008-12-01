# Copyright (C) 2008  Lars Wirzenius <liw@liw.fi>
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


import obnamlib


class Component(object):

    """A piece of data inside an obnamlib.Object.

    Instances of this class store data inside obnamlib.Object objects.
    An Object is a list of Components, and a Component is either a string
    or a list of Components. The distinction between Object and Component
    makes it easier to encode and decode things for on-disk storage:
    Object needs more meta data than Component, for example every Object
    has a unique id, but a Component does not.

    A component has a kind, and the kind determines whether it contains
    a single octet string or other components (never both).

    """

    def __init__(self, kind):
        self.kind = kind
