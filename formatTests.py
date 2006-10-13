import unittest


import wibbrlib.format


class FormatPermissionsTests(unittest.TestCase):

    def testFormatPermissions(self):
        facit = (
            (0000, "---------"),
        )
        for mode, correct in facit:
            self.failUnlessEqual(wibbrlib.format.permissions(mode), correct)
