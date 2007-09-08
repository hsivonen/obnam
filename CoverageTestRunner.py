import coverage
import unittest
import os
import imp
import sys


class CoverageTestResult(unittest.TestResult):

    def __init__(self, output, total):
        unittest.TestResult.__init__(self)
        self.output = output
        self.total = total
        self.lastmsg = ""
        self.coverage_missed = []
        
    def addCoverageMissed(self, filename, statements, missed_statements,
                          missed_description):
        self.coverage_missed.append((filename, statements, missed_statements,
                                     missed_description))

    def wasSuccessful(self):
        return (unittest.TestResult.wasSuccessful(self) and 
                not self.coverage_missed)
        
    def clearmsg(self):
        self.output.write("\b \b" * len(self.lastmsg))
        self.lastmsg = ""
        
    def write(self, test):
        self.clearmsg()
        self.lastmsg = "Running test %d/%d: %s" % (self.testsRun, 
                                                   self.total, 
                                                   str(test)[:50])
        self.output.write(self.lastmsg)
        self.output.flush()
        
    def startTest(self, test):
        unittest.TestResult.startTest(self, test)
        self.write(test)


class CoverageTestRunner:

    """A test runner class that insists modules' tests cover them fully."""
    
    def __init__(self):
        self._module_pairs = []
        
    def add_pair(self, module_pathname, test_module_pathname):
        """Add a module and its test module to list of tests."""
        self._module_pairs.append((module_pathname, test_module_pathname))
        
    def _load_module_from_pathname(self, pathname):
        for tuple in imp.get_suffixes():
            suffix, mode, type = tuple
            if pathname.endswith(suffix):
                name = pathname[:-len(suffix)]
                f = file(pathname, mode)
                return imp.load_module(name, f, pathname, tuple)
        raise Exception("Unknown module: %s" % pathname)

    def _load_pairs(self):
        module_pairs = []
        loader = unittest.defaultTestLoader
        for pathname, test_pathname in self._module_pairs:
            module = self._load_module_from_pathname(pathname)
            test_module = self._load_module_from_pathname(test_pathname)
            suite = loader.loadTestsFromModule(test_module)
            module_pairs.append((module, test_module, suite))
        return module_pairs

    def printErrorList(self, flavor, errors):
        for test, error in errors:
            print "%s: %s" % (flavor, str(test))
            print str(error)

    def run(self):
        module_pairs = self._load_pairs()
        total_tests = sum(suite.countTestCases() 
                          for x, y, suite in module_pairs)
        result = CoverageTestResult(sys.stdout, total_tests)

        for module, test_module, suite in module_pairs:
            coverage.erase()
            coverage.start()
            reload(module)
            suite.run(result)
            coverage.stop()
            filename, stmts, missed, missed_desc = coverage.analysis(module)
            if missed:
                result.addCoverageMissed(filename, stmts, missed, missed_desc)

        sys.stdout.write("\n\n")
        
        if result.wasSuccessful():
            print "OK"
        else:
            print "FAILED"
            print
            if result.errors:
                self.printErrorList("ERROR", result.errors)
            if result.failures:
                self.printErrorList("FAILURE", result.failures)
            if result.coverage_missed:
                print
                print "Statements missed by per-module tests:"
                width = max(len(x[0]) for x in result.coverage_missed)
                fmt = "  %-*s   %s"
                print fmt % (width, "Module", "Missed statements")
                for filename, _, _, desc in sorted(result.coverage_missed):
                    print fmt % (width, filename, desc)

            print "%d failures, %d errors" % (len(result.failures),
                                              len(result.errors))

        return result
