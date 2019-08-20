"""Doctests"""

import doctest
import pkgutil
import hmrc

def load_tests(_loader, tests, _pattern):
    """Run doctest on all modules"""
    for module in pkgutil.walk_packages(hmrc.__path__, hmrc.__name__ + '.'):
        tests.addTests(doctest.DocTestSuite(module.name))
    return tests
