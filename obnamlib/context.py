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


"""Processing context for Obnam"""


import obnamlib


class Context:

    def __init__(self):
        self.config = obnamlib.config.default_config()
        self.cache = None
        self.be = None
        self.map = obnamlib.map.create()
        self.contmap = obnamlib.map.create()
        self.oq = obnamlib.obj.ObjectQueue()
        self.content_oq = obnamlib.obj.ObjectQueue()
        self.progress = obnamlib.progress.ProgressReporter(self.config)
        self.object_cache = None
