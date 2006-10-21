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
