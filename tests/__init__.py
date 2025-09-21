"""
tests/__init__.py
Test package initialization
"""

import os
import sys
import tempfile
import unittest

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)


class BaseTestCase(unittest.TestCase):
    """Base test case with common setup"""

    def setUp(self):
        """Set up test fixtures"""
        self.test_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.test_db.close()

        # Set test environment
        os.environ['FLASK_ENV'] = 'testing'
        os.environ['DATABASE_PATH'] = self.test_db.name

    def tearDown(self):
        """Clean up test fixtures"""
        if os.path.exists(self.test_db.name):
            os.unlink(self.test_db.name)


def run_all_tests():
    """Run all tests in the test suite"""
    loader = unittest.TestLoader()
    suite = loader.discover('tests', pattern='test_*.py')

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)