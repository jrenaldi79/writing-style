#!/usr/bin/env python3
"""
Test Runner - Run all tests with detailed reporting
"""

import sys
import unittest
from pathlib import Path

# Add tests directory to path
sys.path.insert(0, str(Path(__file__).parent))

def run_all_tests(verbose=True):
    """Run all test suites."""
    
    # Discover all tests
    loader = unittest.TestLoader()
    start_dir = Path(__file__).parent
    suite = loader.discover(start_dir, pattern='test_*.py')
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2 if verbose else 1)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")
    print("="*70)
    
    # Return exit code
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    verbose = '--quiet' not in sys.argv
    exit_code = run_all_tests(verbose=verbose)
    sys.exit(exit_code)
