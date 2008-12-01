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


import unittest

import obnamlib


class ComponentKindsTests(unittest.TestCase):

    def testAddsPlainCorrectly(self):
        kinds = obnamlib.ComponentKinds()
        kinds.add_plain(1, "foo")
        self.assert_(kinds.is_plain(kinds.codeof("foo")))

    def testAddsCompositeCorrectly(self):
        kinds = obnamlib.ComponentKinds()
        kinds.add_composite(1, "foo")
        self.assert_(kinds.is_composite(kinds.codeof("foo")))

    def testAddsReferenceCorrectly(self):
        kinds = obnamlib.ComponentKinds()
        kinds.add_ref(1, "foo")
        self.assert_(kinds.is_ref(kinds.codeof("foo")))
