import unittest


import wibbrlib


class ContextCreateTests(unittest.TestCase):

    def test(self):
        context = wibbrlib.context.create()
        attrs = [x for x in dir(context) if not x.startswith("_")]
        attrs.sort()
        self.failUnlessEqual(attrs, ["be", "cache", "config", "map", "oq"])
        self.failUnlessEqual(context.be, None)
        self.failUnlessEqual(context.cache, None)
        self.failIfEqual(context.config, None)
        self.failIfEqual(context.map, None)
        self.failIfEqual(context.oq, None)
