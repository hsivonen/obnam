# Copyright (C) 2008  Lars Wirzenius <liw@liw.fi>
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


import StringIO
import unittest

import obnamlib


class CommandLineUITests(unittest.TestCase):

    def setUp(self):
        self.ui = obnamlib.CommandLineUI("config")
        self.ui.short_help = self.mock_short_help
        self.short_helped = False
        self.ui.commands = {
            "cmd": self.mock_command,
            }

    def mock_short_help(self):
        self.short_helped = True

    def mock_command(self, *args):
        self.args = args

    def test_calls_right_command_function_with_right_args(self):
        self.ui.run(["cmd", "arg1", "arg2"])

    def test_does_not_run_short_help_when_right_command_is_given(self):
        self.ui.run(["cmd", "arg1", "arg2"])
        self.assertFalse(self.short_helped)

    def test_raises_exception_for_unknown_command(self):
        self.assertRaises(obnamlib.Exception, self.ui.run, ["foo"])

    def test_does_not_run_short_help_when_unknown_command_is_given(self):
        try:
            self.ui.run(["foo"])
        except obnamlib.Exception:
            pass
        self.assertFalse(self.short_helped)

    def test_calls_short_help_when_no_arguments_given(self):
        self.ui.run([])
        self.assert_(self.short_helped)

    def test_short_help_writes_output(self):
        ui = obnamlib.CommandLineUI("config")
        f = StringIO.StringIO()
        ui.short_help(stdout=f)
        self.assert_(f.getvalue())
