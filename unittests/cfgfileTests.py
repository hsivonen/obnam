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


"""Unit tests for obnam.cfgfile."""


import unittest

import obnam


class ManipulationTests(unittest.TestCase):

    def setUp(self):
        self.cf = obnam.cfgfile.ConfigFile()
        
    def tearDown(self):
        self.cf = None

    def testEmptySections(self):
        self.failUnlessEqual(self.cf.sections(), [])
        
    def testAddSectionNew(self):
        self.cf.add_section("foo")
        self.failUnlessEqual(self.cf.sections(), ["foo"])
        
    def testAddSectionExisting(self):
        self.cf.add_section("foo")
        self.failUnlessRaises(obnam.cfgfile.DuplicationError,
                              self.cf.add_section,
                              "foo")

    def testHasSectionForExisting(self):
        self.cf.add_section("foo")
        self.failUnless(self.cf.has_section("foo"))

    def testHasSectionForNotExisting(self):
        self.failIf(self.cf.has_section("foo"))


class ParseTests(unittest.TestCase):

    def testEmpty(self):
        cf = obnam.cfgfile.ConfigFile()
        cf.parse_string("")
        self.failUnlessEqual(cf.sections(), [])


unittest.main()
