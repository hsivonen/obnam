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


"""Unit tests for obnam.config."""


import os
import shutil
import StringIO
import unittest


import obnam


class CommandLineParsingTests(unittest.TestCase):

    def config_as_string(self, config):
        f = StringIO.StringIO()
        config.write(f)
        return f.getvalue()

    def testDefaultConfig(self):
        config = obnam.config.default_config()
        self.failUnless(config.has_section("backup"))
        needed = ["block-size", "cache", "store", "target-dir",
                  "host-id", "object-cache-size", "log-level", "ssh-key",
                  "odirect-read", "log-file", "gpg-home", "gpg-encrypt-to",
                  "gpg-sign-with"]
        needed.sort()
        actual = config.options("backup")
        actual.sort()
        self.failUnlessEqual(actual, needed)

    def testEmpty(self):
        config = obnam.config.default_config()
        obnam.config.parse_options(config, [])
        self.failUnlessEqual(self.config_as_string(config), 
                     self.config_as_string(obnam.config.default_config()))

    def testBlockSize(self):
        config = obnam.config.default_config()
        obnam.config.parse_options(config, ["--block-size=12765"])
        self.failUnlessEqual(config.getint("backup", "block-size"), 12765)
        obnam.config.parse_options(config, ["--block-size=42"])
        self.failUnlessEqual(config.getint("backup", "block-size"), 42)

    def testCacheDir(self):
        config = obnam.config.default_config()
        obnam.config.parse_options(config, ["--cache=/tmp/foo"])
        self.failUnlessEqual(config.get("backup", "cache"), "/tmp/foo")

    def testLocalStore(self):
        config = obnam.config.default_config()
        obnam.config.parse_options(config, ["--store=/tmp/foo"])
        self.failUnlessEqual(config.get("backup", "store"), "/tmp/foo")

    def testTargetDir(self):
        config = obnam.config.default_config()
        obnam.config.parse_options(config, ["--target=/tmp/foo"])
        self.failUnlessEqual(config.get("backup", "target-dir"), "/tmp/foo")

    def testObjectCacheSize(self):
        config = obnam.config.default_config()
        obnam.config.parse_options(config, ["--object-cache-size=42"])
        self.failUnlessEqual(config.get("backup", "object-cache-size"), "42")

    def testOdirectRead(self):
        config = obnam.config.default_config()
        obnam.config.parse_options(config, ["--odirect-read=x"])
        self.failUnlessEqual(config.get("backup", "odirect-read"), "x")
