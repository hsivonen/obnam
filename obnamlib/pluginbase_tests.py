# Copyright (C) 2009-2015  Lars Wirzenius
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


import unittest

import obnamlib


class FakeApp(object):

    def __init__(self):
        self.hooks = self


class ObnamPluginTests(unittest.TestCase):

    def setUp(self):
        self.fakeapp = FakeApp()
        self.plugin = obnamlib.ObnamPlugin(self.fakeapp)

    def test_has_an_app(self):
        self.assertEqual(self.plugin.app, self.fakeapp)

    def test_disable_is_implemented(self):
        self.plugin.disable()
