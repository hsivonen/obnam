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
        self.config = obnamlib.config.default_config()
        
    def tearDown(self):
        obnamlib.config.set_default_paths(None)

    def config_as_string(self, config):
        f = StringIO.StringIO()
        config.write(f)
        return f.getvalue()

    def testDefaultConfig(self):
        needed = ["block-size", "cache", "store", "target-dir",
                  "host-id", "object-cache-size", "log-level", "ssh-key",
                  "log-file", "gpg-home", "gpg-encrypt-to",
                  "gpg-sign-with", "no-gpg", "exclude",
                  "report-progress", "generation-times", "snapshot-bytes"]
        actual = self.config.options("backup")
        self.failUnlessEqual(sorted(actual), sorted(needed))

    def testEmpty(self):
        obnamlib.config.parse_options(self.config, [])
        self.failUnlessEqual(self.config_as_string(self.config), 
                     self.config_as_string(obnamlib.config.default_config()))

    def testHostId(self):
        obnamlib.config.parse_options(self.config, ["--host-id=pink"])
        self.failUnlessEqual(self.config.get("backup", "host-id"), "pink")

    def testBlockSize(self):
        obnamlib.config.parse_options(self.config, ["--block-size=42"])
        self.failUnlessEqual(self.config.getint("backup", "block-size"), 42)

    def testCacheDir(self):
        obnamlib.config.parse_options(self.config, ["--cache=/tmp/foo"])
        self.failUnlessEqual(self.config.get("backup", "cache"), "/tmp/foo")

    def testLocalStore(self):
        obnamlib.config.parse_options(self.config, ["--store=/tmp/foo"])
        self.failUnlessEqual(self.config.get("backup", "store"), "/tmp/foo")

    def testTargetDir(self):
        obnamlib.config.parse_options(self.config, ["--target=/foo"])
        self.failUnlessEqual(self.config.get("backup", "target-dir"), "/foo")

    def testObjectCacheSize(self):
        obnamlib.config.parse_options(self.config, ["--object-cache-size=42"])
        self.failUnlessEqual(self.config.get("backup", "object-cache-size"), 
                             "42")

    def testLogFile(self):
        obnamlib.config.parse_options(self.config, ["--log-file=x"])
        self.failUnlessEqual(self.config.get("backup", "log-file"), "x")

    def testLogLevel(self):
        obnamlib.config.parse_options(self.config, ["--log-level=info"])
        self.failUnlessEqual(self.config.get("backup", "log-level"), "info")

    def testSshKey(self):
        obnamlib.config.parse_options(self.config, ["--ssh-key=foo"])
        self.failUnlessEqual(self.config.get("backup", "ssh-key"), "foo")

    def testGpgHome(self):
        obnamlib.config.parse_options(self.config, ["--gpg-home=foo"])
        self.failUnlessEqual(self.config.get("backup", "gpg-home"), "foo")

    def testGpgEncryptTo(self):
        obnamlib.config.parse_options(self.config, ["--gpg-encrypt-to=x"])
        self.failUnlessEqual(self.config.get("backup", "gpg-encrypt-to"), "x")

    def testGpgSignWith(self):
        obnamlib.config.parse_options(self.config, ["--gpg-sign-with=foo"])
        self.failUnlessEqual(self.config.get("backup", "gpg-sign-with"), "foo")

    def testNoGpgIsUnset(self):
        obnamlib.config.parse_options(self.config, [])
        self.failUnlessEqual(self.config.get("backup", "no-gpg"), "false")

    def testNoGpgIsUnsetButDefaultIsTrue(self):
        self.config.set("backup", "no-gpg", "true")
        obnamlib.config.parse_options(self.config, [])
        self.failUnlessEqual(self.config.get("backup", "no-gpg"), "true")

    def testNoGpgIsSet(self):
        obnamlib.config.parse_options(self.config, ["--no-gpg"])
        self.failUnlessEqual(self.config.get("backup", "no-gpg"), "true")

    def testGenerationTimes(self):
        obnamlib.config.parse_options(self.config, ["--generation-times"])
        self.failUnlessEqual(self.config.get("backup", "generation-times"), 
                             "true")

    def testSnapshotBytes(self):
        obnamlib.config.parse_options(self.config, ["--snapshot-bytes=42"])
        self.failUnlessEqual(self.config.getint("backup", "snapshot-bytes"), 
                             42)

    def testExclude(self):
        obnamlib.config.parse_options(self.config, ["--exclude=foo"])
        self.failUnlessEqual(self.config.get("backup", "exclude"), "foo")

    def testReportProgress(self):
        self.failIf(self.config.getboolean("backup", "report-progress"))
        obnamlib.config.parse_options(self.config, ["--progress"])
        self.failUnless(self.config.getboolean("backup", "report-progress"))

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
