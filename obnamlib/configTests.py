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


"""Unit tests for obnamlib.config."""


import os
import shutil
import StringIO
import unittest


import obnamlib


class CommandLineParsingTests(unittest.TestCase):

    def setUp(self):
        obnamlib.config.set_default_paths([])
        
    def tearDown(self):
        obnamlib.config.set_default_paths(None)

    def config_as_string(self, config):
        f = StringIO.StringIO()
        config.write(f)
        return f.getvalue()

    def testDefaultConfig(self):
        config = obnamlib.config.default_config()
        self.failUnless(config.has_section("backup"))
        needed = ["block-size", "cache", "store", "target-dir",
                  "host-id", "object-cache-size", "log-level", "ssh-key",
                  "log-file", "gpg-home", "gpg-encrypt-to",
                  "gpg-sign-with", "no-gpg", "exclude",
                  "report-progress", "generation-times"]
        actual = config.options("backup")
        self.failUnlessEqual(sorted(actual), sorted(needed))

    def testEmpty(self):
        config = obnamlib.config.default_config()
        obnamlib.config.parse_options(config, [])
        self.failUnlessEqual(self.config_as_string(config), 
                     self.config_as_string(obnamlib.config.default_config()))

    def testHostId(self):
        config = obnamlib.config.default_config()
        obnamlib.config.parse_options(config, ["--host-id=pink"])
        self.failUnlessEqual(config.get("backup", "host-id"), "pink")

    def testBlockSize(self):
        config = obnamlib.config.default_config()
        obnamlib.config.parse_options(config, ["--block-size=12765"])
        self.failUnlessEqual(config.getint("backup", "block-size"), 12765)
        obnamlib.config.parse_options(config, ["--block-size=42"])
        self.failUnlessEqual(config.getint("backup", "block-size"), 42)

    def testCacheDir(self):
        config = obnamlib.config.default_config()
        obnamlib.config.parse_options(config, ["--cache=/tmp/foo"])
        self.failUnlessEqual(config.get("backup", "cache"), "/tmp/foo")

    def testLocalStore(self):
        config = obnamlib.config.default_config()
        obnamlib.config.parse_options(config, ["--store=/tmp/foo"])
        self.failUnlessEqual(config.get("backup", "store"), "/tmp/foo")

    def testTargetDir(self):
        config = obnamlib.config.default_config()
        obnamlib.config.parse_options(config, ["--target=/tmp/foo"])
        self.failUnlessEqual(config.get("backup", "target-dir"), "/tmp/foo")

    def testObjectCacheSize(self):
        config = obnamlib.config.default_config()
        obnamlib.config.parse_options(config, ["--object-cache-size=42"])
        self.failUnlessEqual(config.get("backup", "object-cache-size"), "42")

    def testLogFile(self):
        config = obnamlib.config.default_config()
        obnamlib.config.parse_options(config, ["--log-file=x"])
        self.failUnlessEqual(config.get("backup", "log-file"), "x")

    def testLogLevel(self):
        config = obnamlib.config.default_config()
        obnamlib.config.parse_options(config, ["--log-level=info"])
        self.failUnlessEqual(config.get("backup", "log-level"), "info")

    def testSshKey(self):
        config = obnamlib.config.default_config()
        obnamlib.config.parse_options(config, ["--ssh-key=foo"])
        self.failUnlessEqual(config.get("backup", "ssh-key"), "foo")

    def testGpgHome(self):
        config = obnamlib.config.default_config()
        obnamlib.config.parse_options(config, ["--gpg-home=foo"])
        self.failUnlessEqual(config.get("backup", "gpg-home"), "foo")

    def testGpgEncryptTo(self):
        config = obnamlib.config.default_config()
        obnamlib.config.parse_options(config, ["--gpg-encrypt-to=foo"])
        self.failUnlessEqual(config.get("backup", "gpg-encrypt-to"), "foo")

    def testGpgSignWith(self):
        config = obnamlib.config.default_config()
        obnamlib.config.parse_options(config, ["--gpg-sign-with=foo"])
        self.failUnlessEqual(config.get("backup", "gpg-sign-with"), "foo")

    def testNoGpgIsUnset(self):
        config = obnamlib.config.default_config()
        obnamlib.config.parse_options(config, [])
        self.failUnlessEqual(config.get("backup", "no-gpg"), "false")

    def testNoGpgIsUnsetButDefaultIsTrue(self):
        config = obnamlib.config.default_config()
        config.set("backup", "no-gpg", "true")
        obnamlib.config.parse_options(config, [])
        self.failUnlessEqual(config.get("backup", "no-gpg"), "true")

    def testNoGpgIsSet(self):
        config = obnamlib.config.default_config()
        obnamlib.config.parse_options(config, ["--no-gpg"])
        self.failUnlessEqual(config.get("backup", "no-gpg"), "true")

    def testGenerationTimes(self):
        config = obnamlib.config.default_config()
        obnamlib.config.parse_options(config, ["--generation-times"])
        self.failUnlessEqual(config.get("backup", "generation-times"), "true")

    def testExclude(self):
        config = obnamlib.config.default_config()
        obnamlib.config.parse_options(config, ["--exclude=foo"])
        self.failUnlessEqual(config.get("backup", "exclude"), "foo")

    def testReportProgress(self):
        config = obnamlib.config.default_config()
        self.failIf(config.getboolean("backup", "report-progress"))
        obnamlib.config.parse_options(config, ["--progress"])
        self.failUnless(config.getboolean("backup", "report-progress"))

    def testNoConfigs(self):
        parser = obnamlib.config.build_parser()
        options, args = parser.parse_args([])
        self.failUnlessEqual(options.no_configs, False)
        options, args = parser.parse_args(["--no-configs"])
        self.failUnlessEqual(options.no_configs, True)

    def testConfig(self):
        parser = obnamlib.config.build_parser()
        options, args = parser.parse_args([])
        self.failUnlessEqual(options.configs, None)
        options, args = parser.parse_args(["--config=pink"])
        self.failUnlessEqual(options.configs, ["pink"])


class ConfigReadingOptionsTests(unittest.TestCase):

    names = ["tmp.1.conf", "tmp.2.conf", "tmp.3.conf"]

    def setUp(self):
        obnamlib.config.forget_config_file_log()
        for name in self.names:
            f = file(name, "w")
            f.write("[backup]\nblock-size = 1024\n")
            f.close()
        obnamlib.config.set_default_paths(self.names)

    def tearDown(self):
        obnamlib.config.set_default_paths(None)
        for name in self.names:
            if os.path.exists(name):
                os.remove(name)

    def testNoDefaults(self):
        obnamlib.config.set_default_paths([])
        config = obnamlib.config.default_config()
        obnamlib.config.parse_options(config, [])
        self.failUnlessEqual(obnamlib.config.get_config_file_log(), [])

    def testDefaults(self):
        config = obnamlib.config.default_config()
        obnamlib.config.parse_options(config, [])
        self.failUnlessEqual(obnamlib.config.get_config_file_log(), self.names)

    def testNoConfigsOption(self):
        config = obnamlib.config.default_config()
        obnamlib.config.parse_options(config, ["--no-configs"])
        self.failUnlessEqual(obnamlib.config.get_config_file_log(), [])

    def testNoConfigsOptionPlusConfigOption(self):
        config = obnamlib.config.default_config()
        obnamlib.config.parse_options(config, ["--no-configs"] +
                        ["--config=%s" % x for x in self.names])
        self.failUnlessEqual(obnamlib.config.get_config_file_log(), self.names)

    def testDefaultsPlusConfigOption(self):
        config = obnamlib.config.default_config()
        obnamlib.config.parse_options(config, ["--config=/dev/null"])
        self.failUnlessEqual(obnamlib.config.get_config_file_log(), 
                             self.names + ["/dev/null"])


class ConfigFileReadingTests(unittest.TestCase):

    def setUp(self):
        self.filename = "unittest.conf"
        f = file(self.filename, "w")
        f.write("""\
[backup]
store = pink
cache = pretty
""")
        f.close()
        
    def tearDown(self):
        os.remove(self.filename)
    
    def testReadConfigFile(self):
        config = obnamlib.config.default_config()
        obnamlib.config.read_config_file(config, self.filename)
        self.failUnlessEqual(config.get("backup", "store"), "pink")
        self.failUnlessEqual(config.get("backup", "cache"), "pretty")

    def testDefaultConfigsForRoot(self):
        config = obnamlib.config.default_config()
        obnamlib.config.set_uid_and_home(0, "/root")
        configs = obnamlib.config.get_default_paths()
        self.failUnlessEqual(configs,
                             ["/usr/share/obnam/obnam.conf",
                              "/etc/obnam/obnam.conf"])

    def testDefaultConfigsForUser(self):
        config = obnamlib.config.default_config()
        obnamlib.config.set_uid_and_home(12765, "/home/pretty")
        configs = obnamlib.config.get_default_paths()
        self.failUnlessEqual(configs,
                             ["/usr/share/obnam/obnam.conf",
                              "/home/pretty/.obnam/obnam.conf"])


class PrintOptionsTests(unittest.TestCase):

    def test(self):
        f = StringIO.StringIO()
        obnamlib.config.print_option_names(f=f)
        self.failIfEqual(f.getvalue(), "")


class WriteDefaultConfigTests(unittest.TestCase):

    def test(self):
        config = obnamlib.config.default_config()
        f = StringIO.StringIO()
        obnamlib.config.write_defaultconfig(config, output=f)
        s = f.getvalue()
        self.failUnless(s.startswith("import socket"))
        self.failUnless("\nitems =" in s)


class GetUidAndHomeTests(unittest.TestCase):

    def testGetUid(self):
        obnamlib.config.set_uid_and_home(None, None)
        self.failIfEqual(obnamlib.config.get_uid(), None)

    def testGetHome(self):
        obnamlib.config.set_uid_and_home(None, None)
        self.failIfEqual(obnamlib.config.get_home(), None)

    def testGetUidFaked(self):
        obnamlib.config.set_uid_and_home(42, "pretty")
        self.failUnlessEqual(obnamlib.config.get_uid(), 42)

    def testGetHomeFaked(self):
        obnamlib.config.set_uid_and_home(42, "pink")
        self.failUnlessEqual(obnamlib.config.get_home(), "pink")
