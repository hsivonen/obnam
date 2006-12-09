# testrun.py -- run unit tests for Obnam
#
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


import unittest
import os
import sys

suite = unittest.TestSuite()
for py in [py for py in os.listdir("unittests") if py.endswith("Tests.py")]:
    py = os.path.join("unittests", py)
    suite.addTest(unittest.defaultTestLoader.loadTestsFromName(py[:-3]))

runner = unittest.TextTestRunner()
result = runner.run(suite)
if result.wasSuccessful():
    sys.exit(0)
else:
    sys.exit(1)
