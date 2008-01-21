# Copyright (C) 2006, 2007  Lars Wirzenius <liw@iki.fi>
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


"""Unit tests for app.py."""


import unittest

import obnam


class ApplicationTests(unittest.TestCase):

    def setUp(self):
        context = obnam.context.Context()
        self.app = obnam.Application(context)

    def testHasEmptyListOfRootsInitially(self):
        self.failUnlessEqual(self.app.get_roots(), [])

    def testKeepsListOfRootsCorrectly(self):
        self.app.add_root("pink")
        self.app.add_root("pretty")
        self.failUnlessEqual(self.app.get_roots(), ["pink", "pretty"])

    def testReturnsEmptyExclusionListInitially(self):
        self.failUnlessEqual(self.app.get_exclusion_regexps(), [])
