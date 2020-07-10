import unittest
import os.path

import rukzuk.tests


def suite():
    test_suite = unittest.TestSuite()
    test_suite.addTests(unittest.TestLoader().discover(os.path.dirname(__file__)))
    test_suite.addTests(unittest.TestLoader().loadTestsFromTestCase(
        rukzuk.tests.OpenSSLTest))
    return test_suite
