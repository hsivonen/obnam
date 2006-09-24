import unittest
import os

suite = unittest.TestSuite()
for py in [py for py in os.listdir(".") if py.endswith("Tests.py")]:
    suite.addTest(unittest.defaultTestLoader.loadTestsFromName(py[:-3]))

runner = unittest.TextTestRunner()
runner.run(suite)
