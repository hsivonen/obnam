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

from CoverageTestRunner import CoverageTestRunner


if len(sys.argv) == 1:
    files = [os.path.join("unittests", x) 
             for x in os.listdir("unittests") if x.endswith("Tests.py")]
else:
    files = sys.argv[1:]
runner = CoverageTestRunner()
for testpath in files:
    basename = os.path.basename(testpath)
    codepath = os.path.join("obnam", basename[:-len("Tests.py")] + ".py")
    runner.add_pair(codepath, testpath)

result = runner.run()
if result.wasSuccessful():
    sys.exit(0)
else:
    sys.exit(1)
