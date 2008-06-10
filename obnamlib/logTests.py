# Copyright (C) 2007  Lars Wirzenius <liw@iki.fi>
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


"""Unit tests for obnam.log"""


import os
import stat
import unittest

import obnam


class LogTests(unittest.TestCase):

    filename = "unittest.testlog"

    def setUp(self):
        if os.path.exists(self.filename):
            os.remove(self.filename)
        
    tearDown = setUp

    def testCreateNew(self):
        self.failIf(os.path.exists(self.filename))

        config = obnam.config.default_config()
        config.set("backup", "log-file", self.filename)

        obnam.log.setup(config)
        self.failUnless(os.path.exists(self.filename))
        
        st = os.stat(self.filename)
        self.failUnless(stat.S_ISREG(st.st_mode))
        self.failUnlessEqual(stat.S_IMODE(st.st_mode), 0600)
