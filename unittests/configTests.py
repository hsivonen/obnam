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

    def setUp(self):
        obnam.config.set_default_paths([])
        
    def tearDown(self):
        obnam.config.set_default_paths(None)

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
                  "gpg-sign-with", "no-gpg", "exclude", "odirect-pipe",
                  "report-progress", "generation-times"]
        needed.sort()
        actual = config.options("backup")
        actual.sort()
        self.failUnlessEqual(actual, needed)

    def testEmpty(self):
        config = obnam.config.default_config()
        obnam.config.parse_options(config, [])
        self.failUnlessEqual(self.config_as_string(config), 
                     self.config_as_string(obnam.config.default_config()))

    def testHostId(self):
        config = obnam.config.default_config()
        obnam.config.parse_options(config, ["--host-id=pink"])
        self.failUnlessEqual(config.get("backup", "host-id"), "pink")

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

    def testOdirectPipe(self):
        config = obnam.config.default_config()
        obnam.config.parse_options(config, ["--odirect-pipe=x"])
        self.failUnlessEqual(config.get("backup", "odirect-pipe"), "x")

    def testLogFile(self):
        config = obnam.config.default_config()
        obnam.config.parse_options(config, ["--log-file=x"])
        self.failUnlessEqual(config.get("backup", "log-file"), "x")

    def testLogLevel(self):
        config = obnam.config.default_config()
        obnam.config.parse_options(config, ["--log-level=info"])
        self.failUnlessEqual(config.get("backup", "log-level"), "info")

    def testSshKey(self):
        config = obnam.config.default_config()
        obnam.config.parse_options(config, ["--ssh-key=foo"])
        self.failUnlessEqual(config.get("backup", "ssh-key"), "foo")

    def testGpgHome(self):
        config = obnam.config.default_config()
        obnam.config.parse_options(config, ["--gpg-home=foo"])
        self.failUnlessEqual(config.get("backup", "gpg-home"), "foo")

    def testGpgEncryptTo(self):
        config = obnam.config.default_config()
        obnam.config.parse_options(config, ["--gpg-encrypt-to=foo"])
        self.failUnlessEqual(config.get("backup", "gpg-encrypt-to"), "foo")

    def testGpgSignWith(self):
        config = obnam.config.default_config()
        obnam.config.parse_options(config, ["--gpg-sign-with=foo"])
        self.failUnlessEqual(config.get("backup", "gpg-sign-with"), "foo")

    def testNoGpg(self):
        config = obnam.config.default_config()
        obnam.config.parse_options(config, ["--no-gpg"])
        self.failUnlessEqual(config.get("backup", "no-gpg"), "true")

    def testUsePsyco(self):
        config = obnam.config.default_config()
        obnam.config.parse_options(config, ["--use-psyco"])

    def testExclude(self):
        config = obnam.config.default_config()
        obnam.config.parse_options(config, ["--exclude=foo"])
        self.failUnlessEqual(config.get("backup", "exclude"), "foo")

    def testReportProgress(self):
        config = obnam.config.default_config()
        self.failIf(config.getboolean("backup", "report-progress"))
        obnam.config.parse_options(config, ["--progress"])
        self.failUnless(config.getboolean("backup", "report-progress"))

    def testNoConfigs(self):
        parser = obnam.config.build_parser()
        options, args = parser.parse_args([])
        self.failUnlessEqual(options.no_configs, False)
        options, args = parser.parse_args(["--no-configs"])
        self.failUnlessEqual(options.no_configs, True)

    def testConfig(self):
        parser = obnam.config.build_parser()
        options, args = parser.parse_args([])
        self.failUnlessEqual(options.configs, None)
        options, args = parser.parse_args(["--config=pink"])
        self.failUnlessEqual(options.configs, ["pink"])


class ConfigReadingOptionsTests(unittest.TestCase):

    names = ["tmp.1.conf", "tmp.2.conf", "tmp.3.conf"]

    def setUp(self):
        obnam.config.forget_config_file_log()
        for name in self.names:
            f = file(name, "w")
            f.write("[backup]\nblock-size = 1024\n")
            f.close()
        obnam.config.set_default_paths(self.names)

    def tearDown(self):
        obnam.config.set_default_paths(None)
        for name in self.names:
            if os.path.exists(name):
                os.remove(name)

    def testNoDefaults(self):
        obnam.config.set_default_paths([])
        config = obnam.config.default_config()
        obnam.config.parse_options(config, [])
        self.failUnlessEqual(obnam.config.get_config_file_log(), [])

    def testDefaults(self):
        config = obnam.config.default_config()
        obnam.config.parse_options(config, [])
        self.failUnlessEqual(obnam.config.get_config_file_log(), self.names)

    def testNoConfigsOption(self):
        config = obnam.config.default_config()
        obnam.config.parse_options(config, ["--no-configs"])
        self.failUnlessEqual(obnam.config.get_config_file_log(), [])

    def testNoConfigsOptionPlusConfigOption(self):
        config = obnam.config.default_config()
        obnam.config.parse_options(config, ["--no-configs"] +
                        ["--config=%s" % x for x in self.names])
        self.failUnlessEqual(obnam.config.get_config_file_log(), self.names)

    def testDefaultsPlusConfigOption(self):
        config = obnam.config.default_config()
        obnam.config.parse_options(config, ["--config=/dev/null"])
        self.failUnlessEqual(obnam.config.get_config_file_log(), 
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
        config = obnam.config.default_config()
        obnam.config.read_config_file(config, self.filename)
        self.failUnlessEqual(config.get("backup", "store"), "pink")
        self.failUnlessEqual(config.get("backup", "cache"), "pretty")

    def testDefaultConfigsForRoot(self):
        config = obnam.config.default_config()
        obnam.config.set_uid_and_home(0, "/root")
        configs = obnam.config.get_default_paths()
        self.failUnlessEqual(configs,
                             ["/usr/share/obnam/obnam.conf",
                              "/etc/obnam/obnam.conf"])

    def testDefaultConfigsForUser(self):
        config = obnam.config.default_config()
        obnam.config.set_uid_and_home(12765, "/home/pretty")
        configs = obnam.config.get_default_paths()
        self.failUnlessEqual(configs,
                             ["/usr/share/obnam/obnam.conf",
                              "/home/pretty/.obnam/obnam.conf"])
