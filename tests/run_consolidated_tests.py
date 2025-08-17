#!/usr/bin/env python3
"""
Consolidated Test Runner

This script runs all consolidated test files to provide a comprehensive test suite.
It replaces the previous scattered test files with organized, consolidated test modules.

Usage:
    python run_consolidated_tests.py [options]

Options:
    --mock-only      Run only mock tests
    --real-only      Run only real integration tests
    --fast           Run fast tests only (skip slow integration tests)
    --verbose        Verbose output
    --coverage       Run with coverage reporting
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path


def run_tests(test_paths, options):
    """Run tests with the given options"""
    cmd = ["/Users/jesse.thaloor/Developer/python/bbctams/bin/python", "-m", "pytest"]
    
    # Add test paths
    cmd.extend(test_paths)
    
    # Add options
    if options.verbose:
        cmd.append("-v")
    
    if options.coverage:
        cmd.extend(["--cov=app", "--cov-report=html", "--cov-report=term"])
    
    # Add pytest options
    cmd.extend([
        "--tb=short",
        "--strict-markers",
        "--disable-warnings"
    ])
    
    print(f"Running tests with command: {' '.join(cmd)}")
    print(f"Test paths: {test_paths}")
    print("-" * 80)
    
    try:
        result = subprocess.run(cmd, cwd=Path(__file__).parent)
        return result.returncode
    except KeyboardInterrupt:
        print("\nTests interrupted by user")
        return 1
    except Exception as e:
        print(f"Error running tests: {e}")
        return 1


def get_test_paths(options):
    """Get test paths based on options"""
    base_dir = Path(__file__).parent
    
    if options.mock_only:
        return [str(base_dir / "mock_tests")]
    elif options.real_only:
        return [str(base_dir / "real_tests")]
    elif options.performance_only:
        return [str(base_dir / "performance_tests")]
    else:
        # Run all tests except performance tests (integration focus)
        return [
            str(base_dir / "mock_tests"),
            str(base_dir / "real_tests")
        ]


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Run consolidated TAMS tests")
    parser.add_argument("--mock-only", action="store_true", help="Run only mock tests")
    parser.add_argument("--real-only", action="store_true", help="Run only real integration tests")
    parser.add_argument("--performance-only", action="store_true", help="Run only performance tests")
    parser.add_argument("--fast", action="store_true", help="Run fast tests only")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--coverage", action="store_true", help="Run with coverage reporting")
    
    args = parser.parse_args()
    
    # Validate options
    if sum([args.mock_only, args.real_only, args.performance_only]) > 1:
        print("Error: Cannot specify multiple test types")
        return 1
    
    # Get test paths
    test_paths = get_test_paths(args)
    
    # Print test summary
    print("TAMS Consolidated Test Suite (Integration Focus)")
    print("=" * 80)
    if args.performance_only:
        print(f"Performance tests: {len(list(Path(test_paths[0]).glob('test_*.py')))} files")
    else:
        print(f"Mock tests: {len(list(Path(test_paths[0]).glob('test_*.py')))} files")
        if len(test_paths) > 1:
            print(f"Real tests: {len(list(Path(test_paths[1]).glob('test_*.py')))} files")
    print(f"Total test files: {sum(len(list(Path(p).glob('test_*.py'))) for p in test_paths)}")
    print()
    
    # Run tests
    return run_tests(test_paths, args)


if __name__ == "__main__":
    sys.exit(main())
