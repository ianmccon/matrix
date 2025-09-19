import unittest
import sys
import os

def main():
    # Ensure project root is in sys.path
    project_root = os.path.dirname(os.path.abspath(__file__))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    # Discover and run all tests in the tests/ directory
    loader = unittest.TestLoader()
    suite = loader.discover(os.path.join(project_root, 'tests'))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(not result.wasSuccessful())

if __name__ == '__main__':
    main()
