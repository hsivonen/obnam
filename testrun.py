import unittest
import os
import sys

suite = unittest.TestSuite()
for py in [py for py in os.listdir(".") if py.endswith("Tests.py")]:
    suite.addTest(unittest.defaultTestLoader.loadTestsFromName(py[:-3]))

runner = unittest.TextTestRunner()
result = runner.run(suite)
if result.errors == 0:
    sys.exit(0)
else:
    sys.exit(1)

