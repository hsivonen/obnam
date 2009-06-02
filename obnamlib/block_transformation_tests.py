# Copyright (C) 2009  Lars Wirzenius <liw@liw.fi>
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


class MockOptions:

    def __init__(self):
        self.use_gzip = False
        self.gpg_home = "sample-gpg-home"
        self.encrypt_to = "490C9ED1"
        self.sign_with = "490C9ED1"


class BlockTransformationTests(unittest.TestCase):

    def test_reversibility(self):
        blob = "lorem ipsum"
        options = MockOptions()
        for klass in obnamlib.block_transformations:
            transform = klass()
            transform.configure(options)
            to_blob = transform.to_fs(blob)
            from_blob = transform.from_fs(to_blob)
            self.failUnlessEqual(blob, from_blob)
