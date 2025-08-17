#!/usr/bin/env python3
"""
Performance Test Runner

This script runs performance and stress tests for the TAMS system.
These tests are separate from integration tests and focus on:
- Performance benchmarking
- Stress testing under load
- Scalability testing
- Memory usage monitoring
- Concurrent operation testing

Usage:
    python run_performance_tests.py [options]

Options:
    --fast           Run fast performance tests only
    --stress         Run stress tests only
    --scalability    Run scalability tests only
    --verbose        Verbose output
    --coverage       Run with coverage reporting
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path


def run_performance_tests(test_paths, options):
    """Run performance tests with the given options"""
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
        "--disable-warnings",
        "--durations=10"  # Show top 10 slowest tests
    ])
    
    print(f"Running performance tests with command: {' '.join(cmd)}")
    print(f"Test paths: {test_paths}")
    print("-" * 80)
    
    try:
        result = subprocess.run(cmd, cwd=Path(__file__).parent)
        return result.returncode
    except KeyboardInterrupt:
        print("\nPerformance tests interrupted by user")
        return 1
    except Exception as e:
        print(f"Error running performance tests: {e}")
        return 1


def get_performance_test_paths(options):
    """Get performance test paths based on options"""
    base_dir = Path(__file__).parent / "performance_tests"
    
    if options.fast:
        return [str(base_dir / "test_performance_stress_real.py::TestPerformanceReal")]
    elif options.stress:
        return [str(base_dir / "test_performance_stress_real.py::TestStressReal")]
    elif options.scalability:
        return [str(base_dir / "test_performance_stress_real.py::TestScalabilityReal")]
    else:
        # Run all performance tests
        return [str(base_dir)]


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Run TAMS Performance Tests")
    parser.add_argument("--fast", action="store_true", help="Run fast performance tests only")
    parser.add_argument("--stress", action="store_true", help="Run stress tests only")
    parser.add_argument("--scalability", action="store_true", help="Run scalability tests only")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--coverage", action="store_true", help="Run with coverage reporting")
    
    args = parser.parse_args()
    
    # Validate options
    if sum([args.fast, args.stress, args.scalability]) > 1:
        print("Error: Cannot specify multiple test types")
        return 1
    
    # Get test paths
    test_paths = get_performance_test_paths(args)
    
    # Print test summary
    print("TAMS Performance Test Suite")
    print("=" * 80)
    print(f"Performance tests: {len(list(Path(test_paths[0]).parent.glob('test_*.py')))} files")
    print(f"Total test files: {len(test_paths)}")
    print()
    
    # Run tests
    return run_performance_tests(test_paths, args)


if __name__ == "__main__":
    sys.exit(main())
