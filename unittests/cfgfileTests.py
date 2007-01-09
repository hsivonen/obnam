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


import StringIO
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

    def testRemoveSectionNonExistentSection(self):
        self.failUnlessEqual(self.cf.remove_section("foo"), False)

    def testRemoveSectionExistingSection(self):
        self.cf.add_section("foo")
        self.failUnlessEqual(self.cf.remove_section("foo"), True)


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

    def testGetIntNonInteger(self):
        self.cf.add_section("foo")
        self.cf.set("foo", "bar", "foobar")
        self.failUnlessRaises(ValueError,
                              self.cf.getint,
                              "foo", "bar")

    def testGetIntDecimalInteger(self):
        self.cf.add_section("foo")
        self.cf.set("foo", "bar", "12765")
        self.failUnlessEqual(self.cf.getint("foo", "bar"), 12765)

    def testGetIntHexadecimalInteger(self):
        self.cf.add_section("foo")
        self.cf.set("foo", "bar", "0x12765")
        self.failUnlessEqual(self.cf.getint("foo", "bar"), 0x12765)

    def testGetIntOctalInteger(self):
        self.cf.add_section("foo")
        self.cf.set("foo", "bar", "033")
        self.failUnlessEqual(self.cf.getint("foo", "bar"), 3*8 + 3)

    def testGetFloatNonFloat(self):
        self.cf.add_section("foo")
        self.cf.set("foo", "bar", "foobar")
        self.failUnlessRaises(ValueError,
                              self.cf.getfloat,
                              "foo", "bar")

    def testGetFloat(self):
        self.cf.add_section("foo")
        self.cf.set("foo", "bar", "12.765")
        self.failUnlessEqual(self.cf.getfloat("foo", "bar"), 12.765)

    def testGetBooleanBad(self):
        self.cf.add_section("foo")
        self.cf.set("foo", "bar", "foobar")
        self.failUnlessRaises(ValueError,
                              self.cf.getboolean,
                              "foo", "bar")

    def testGetBooleanTrue(self):
        self.cf.add_section("foo")
        for x in ["yes", "true", "on", "1"]:
            self.cf.set("foo", "bar", x)
            self.failUnlessEqual(self.cf.getboolean("foo", "bar"), True)

    def testGetBooleanFalse(self):
        self.cf.add_section("foo")
        for x in ["no", "false", "off", "0"]:
            self.cf.set("foo", "bar", x)
            self.failUnlessEqual(self.cf.getboolean("foo", "bar"), False)

    def testItemsNonExistentSection(self):
        self.failUnlessRaises(obnam.cfgfile.NoSectionError,
                              self.cf.items,
                              "foo")

    def testItemsEmpty(self):
        self.cf.add_section("foo")
        self.failUnlessEqual(self.cf.items("foo"), [])

    def testItemsNonEmpty(self):
        self.cf.add_section("foo")
        options = ["%d" % x for x in range(4)]
        for option in options:
            self.cf.append("foo", option, option)
            self.cf.append("foo", option, option)
        self.failUnlessEqual(self.cf.items("foo"), 
                             [("0", ["0", "0"]),
                              ("1", ["1", "1"]),
                              ("2", ["2", "2"]),
                              ("3", ["3", "3"])])

    def testRemoveOptionNonExistentSection(self):
        self.failUnlessRaises(obnam.cfgfile.NoSectionError,
                              self.cf.remove_option,
                              "foo", "bar")

    def testRemoveOptionNonExistentOption(self):
        self.cf.add_section("foo")
        self.failUnlessEqual(self.cf.remove_option("foo", "bar"), False)

    def testRemoveOptionExistingOption(self):
        self.cf.add_section("foo")
        self.cf.set("foo", "bar", "foobar")
        self.failUnlessEqual(self.cf.remove_option("foo", "bar"), True)
        self.failUnlessEqual(self.cf.items("foo"), [])


class WriteTests(unittest.TestCase):

    def testSingleValue(self):
        cf = obnam.cfgfile.ConfigFile()
        cf.add_section("foo")
        cf.set("foo", "bar", "foobar")
        f = StringIO.StringIO()
        cf.write(f)
        self.failUnlessEqual(f.getvalue(), """\
[foo]
bar = foobar
""")

    def testMultiValue(self):
        cf = obnam.cfgfile.ConfigFile()
        cf.add_section("foo")
        cf.append("foo", "bar", "foobar")
        cf.append("foo", "bar", "baz")
        f = StringIO.StringIO()
        cf.write(f)
        self.failUnlessEqual(f.getvalue(), """\
[foo]
bar = foobar
bar = baz
""")


class ReadTests(unittest.TestCase):

    def parse(self, file_contents):
        cf = obnam.cfgfile.ConfigFile()
        f = StringIO.StringIO(file_contents)
        cf.readfp(f)
        return cf

    def testEmpty(self):
        cf = self.parse("")
        self.failUnlessEqual(cf.sections(), [])

    def testEmptySection(self):
        cf = self.parse("[foo]\n")
        self.failUnlessEqual(cf.sections(), ["foo"])

    def testTwoEmptySection(self):
        cf = self.parse("[foo]\n[bar]\n")
        self.failUnlessEqual(cf.sections(), ["bar", "foo"])

    def testSameSectionTwice(self):
        self.failUnlessRaises(obnam.cfgfile.DuplicationError,
                              self.parse,
                              "[foo]\n[foo]\n")

    def testParsingError(self):
        self.failUnlessRaises(obnam.cfgfile.ParsingError,
                              self.parse, "xxxx")

    def testComment(self):
        cf = self.parse("# blah\n[foo]\n\n\n")
        self.failUnlessEqual(cf.sections(), ["foo"])

    def testSingleLineSingleValue(self):
        cf = self.parse("[foo]\nbar = foobar\n")
        self.failUnlessEqual(cf.get("foo", "bar"), "foobar")

    def testSingleLineTwoValues(self):
        cf = self.parse("[foo]\nbar = foobar\nbar = baz\n")
        self.failUnlessEqual(cf.get("foo", "bar"), ["foobar", "baz"])

    def testContinuationLine(self):
        cf = self.parse("[foo]\nbar = \n foobar\n")
        self.failUnlessEqual(cf.get("foo", "bar"), " foobar")


class ReadWriteTest(unittest.TestCase):

    def test(self):
        cf = obnam.cfgfile.ConfigFile()
        cf.add_section("foo")
        cf.append("foo", "bar", "foobar")
        cf.append("foo", "bar", "baz")
        f = StringIO.StringIO()
        cf.write(f)
        f.seek(0, 0)
        cf2 = obnam.cfgfile.ConfigFile()
        cf2.readfp(f)
        self.failUnlessEqual(cf2.sections(), ["foo"])
        self.failUnlessEqual(cf2.items("foo"), [("bar", ["foobar", "baz"])])
