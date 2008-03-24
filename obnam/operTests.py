# Copyright (C) 2008  Lars Wirzenius <liw@iki.fi>
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


"""Tests for obnam.oper."""


import unittest

import obnam


class OperationTests(unittest.TestCase):

    def setUp(self):
        context = obnam.context.Context()
        self.app = obnam.Application(context)
        self.args = ["pink", "pretty"]
        self.op = obnam.Operation(self.app, self.args)

    def testNameIsNone(self):
        self.failUnlessEqual(self.op.name, None)

    def testHasRightApplication(self):
        self.failUnlessEqual(self.op.get_application(), self.app)

    def testHasRightArgs(self):
        self.failUnlessEqual(self.op.get_args(), self.args)


class OperationFactoryTests(unittest.TestCase):
    
    def setUp(self):
        context = obnam.context.Context()
        self.app = obnam.Application(context)
        self.factory = obnam.OperationFactory(self.app)
    
    def testFindsOperations(self):
        self.failUnless(self.factory.find_operations())

    def testRaisesErrorForNoArguments(self):
        self.failUnlessRaises(obnam.ObnamException, 
                              self.factory.get_operation, [])

    def testRaisesErrorForUnknownArgument(self):
        self.failUnlessRaises(obnam.ObnamException, 
                              self.factory.get_operation, ["pink"])

    def testFindsBackupOperation(self):
        self.failUnless(self.factory.get_operation(["backup"]))
