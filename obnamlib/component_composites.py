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


import obnamlib


# This module contains the component classes that are simple composite
# ones. They don't need any extra testing. There are, however, so many
# of them that it's pointless putting each in its own module.


class File(obnamlib.CompositeComponent):

    composite_kind = obnamlib.FILE


class NameIPair(obnamlib.CompositeComponent):

    composite_kind = obnamlib.NAMEIPAIR


class ObjMap(obnamlib.CompositeComponent):

    composite_kind = obnamlib.OBJMAP
