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


class SectionTests(unittest.TestCase):

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

    def testSectionsEmpty(self):
        self.failUnlessEqual(self.cf.sections(), [])

    def testSectionsOne(self):
        self.cf.add_section("foo")
        self.failUnlessEqual(self.cf.sections(), ["foo"])

    def testSectionsMany(self):
        list = ["%d" % x for x in range(100)]
        for section in list:
            self.cf.add_section(section)
        self.failUnlessEqual(self.cf.sections(), sorted(list))


class OptionsTests(unittest.TestCase):

    def setUp(self):
        self.cf = obnam.cfgfile.ConfigFile()
        
    def tearDown(self):
        self.cf = None
        
    def testOptionsNonExistentSection(self):
        self.failUnlessRaises(obnam.cfgfile.NoSectionError,
                              self.cf.options,
                              "foo")

    def testOptionsEmptySection(self):
        self.cf.add_section("foo")
        self.failUnlessEqual(self.cf.options("foo"), [])

    def testOptionsNonEmptySection(self):
        self.cf.add_section("foo")
        options = ["%d" % x for x in range(100)]
        for option in options:
            self.cf.set("foo", option, option)
        self.failUnlessEqual(self.cf.options("foo"), sorted(options))

    def testHasOptionNonExistingSection(self):
        self.failUnlessRaises(obnam.cfgfile.NoSectionError,
                              self.cf.has_option,
                              "foo", "bar")

    def testHasOptionNonExistingOption(self):
        self.cf.add_section("foo")
        self.failIf(self.cf.has_option("foo", "bar"))

    def testHasOptionExistingOption(self):
        self.cf.add_section("foo")
        self.cf.set("foo", "bar", "foobar")
        self.failUnless(self.cf.has_option("foo", "bar"))

    def testGetNonExistingSection(self):
        self.failUnlessRaises(obnam.cfgfile.NoSectionError,
                              self.cf.get,
                              "foo", "bar")

    def testGetNonExistingOption(self):
        self.cf.add_section("foo")
        self.failUnlessRaises(obnam.cfgfile.NoOptionError,
                              self.cf.get,
                              "foo", "bar")

    def testSetNonExistingSection(self):
        self.failUnlessRaises(obnam.cfgfile.NoSectionError,
                              self.cf.set,
                              "foo", "bar", "foobar")

    def testSetAndGet(self):
        self.cf.add_section("foo")
        self.cf.set("foo", "bar", "foobar")
        self.failUnlessEqual(self.cf.get("foo", "bar"), "foobar")

    def testAppendNonExistingSection(self):
        self.failUnlessRaises(obnam.cfgfile.NoSectionError,
                              self.cf.append,
                              "foo", "bar", "foobar")

    def testAppendFirstValue(self):
        self.cf.add_section("foo")
        self.cf.append("foo", "bar", "foobar")
        self.failUnlessEqual(self.cf.get("foo", "bar"), "foobar")

    def testAppendSecondValue(self):
        self.cf.add_section("foo")
        self.cf.append("foo", "bar", "foobar")
        self.cf.append("foo", "bar", "baz")
        self.failUnlessEqual(self.cf.get("foo", "bar"), ["foobar", "baz"])

    def testOptionXform(self):
        self.cf.add_section("foo")
        self.cf.set("foo", "BAR", "foobar")
        self.failUnless(self.cf.has_option("foo", "bar"))
        self.failUnlessEqual(self.cf.options("foo"), ["bar"])
        self.failUnlessEqual(self.cf.get("foo", "bar"), "foobar")


class ParseTests(unittest.TestCase):

    def testEmpty(self):
        cf = obnam.cfgfile.ConfigFile()
        cf.parse_string("")
        self.failUnlessEqual(cf.sections(), [])


unittest.main()
