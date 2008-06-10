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


"""Unit tests for obnamlib.context."""


import unittest


import obnamlib


class ContextCreateTests(unittest.TestCase):

    def test(self):
        context = obnamlib.context.Context()
        attrs = [x for x in dir(context) if not x.startswith("_")]
        attrs.sort()
        self.failUnlessEqual(attrs, 
            ["be", "cache", "config", "content_oq", "contmap", "map", "object_cache", 
             "oq", "progress"])
        self.failUnlessEqual(context.be, None)
        self.failUnlessEqual(context.cache, None)
        self.failIfEqual(context.config, None)
        self.failIfEqual(context.map, None)
        self.failIfEqual(context.oq, None)
        self.failIfEqual(context.content_oq, None)
        self.failUnlessEqual(context.object_cache, None)
