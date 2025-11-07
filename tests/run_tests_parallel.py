#!/usr/bin/env python3
"""
Parallel Test Runner

This script runs test sections (files) in parallel, with tests within each section
also running in parallel using pytest-xdist.

Usage:
    python run_tests_parallel.py [test_files...]
    
    If no test files are specified, runs all router comprehensive tests.
"""

import subprocess
import sys
import os
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
import argparse
import time

# Get the test directory
TEST_DIR = Path(__file__).parent
PROJECT_ROOT = TEST_DIR.parent
PYTHON_BIN = "/Users/jesse.thaloor/Developer/python/vasttams/bin/python"

# Default test files to run if none specified
DEFAULT_TEST_FILES = [
    "tests/flows/test_router_comprehensive.py",
    "tests/analytics/test_router.py",
    "tests/objects/test_router_comprehensive.py",
    "tests/sources/test_router_comprehensive.py",
    "tests/segments/test_router_comprehensive.py",
    "tests/hls/test_router_comprehensive.py",
    "tests/storagebackends/test_router_comprehensive.py",
    "tests/service/test_router_comprehensive.py",
    "tests/auth/test_router_comprehensive.py",
]


def run_test_file(test_file, python_bin=None, workers=None):
    """
    Run a single test file in parallel.
    
    Args:
        test_file: Path to test file (relative to project root)
        python_bin: Python binary to use
        workers: Number of workers for pytest-xdist (None = auto)
    
    Returns:
        tuple: (test_file, return_code, stdout, stderr, duration)
    """
    if python_bin is None:
        python_bin = PYTHON_BIN
    
    # Build pytest command
    cmd = [
        python_bin,
        "-m", "pytest",
        str(test_file),
        "-v",
    ]
    
    # Add pytest-xdist for parallel execution within the file
    if workers:
        cmd.extend(["-n", str(workers)])
    else:
        cmd.extend(["-n", "auto"])
    
    start_time = time.time()
    
    try:
        result = subprocess.run(
            cmd,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=600,  # 10 minute timeout per file
        )
        duration = time.time() - start_time
        
        return (
            test_file,
            result.returncode,
            result.stdout,
            result.stderr,
            duration
        )
    except subprocess.TimeoutExpired:
        duration = time.time() - start_time
        return (
            test_file,
            124,  # Timeout exit code
            "",
            f"Test file timed out after {duration:.1f} seconds",
            duration
        )
    except Exception as e:
        duration = time.time() - start_time
        return (
            test_file,
            1,
            "",
            f"Error running test file: {e}",
            duration
        )


def run_tests_parallel(test_files, max_workers=None, file_workers=None):
    """
    Run multiple test files in parallel, with tests within each file also running in parallel.
    
    Args:
        test_files: List of test file paths
        max_workers: Maximum number of test files to run in parallel (None = auto)
        file_workers: Number of workers per test file (None = auto)
    
    Returns:
        dict: Results summary with pass/fail counts
    """
    if max_workers is None:
        # Default to number of CPU cores, but cap at number of test files
        import multiprocessing
        max_workers = min(multiprocessing.cpu_count(), len(test_files))
    
    print(f"Running {len(test_files)} test files in parallel")
    print(f"Max parallel files: {max_workers}")
    print(f"Workers per file: {file_workers or 'auto'}")
    print("-" * 80)
    
    results = {
        "passed": [],
        "failed": [],
        "total_duration": 0,
    }
    
    start_time = time.time()
    
    # Run test files in parallel
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        # Submit all test files
        future_to_file = {
            executor.submit(run_test_file, test_file, PYTHON_BIN, file_workers): test_file
            for test_file in test_files
        }
        
        # Process results as they complete
        for future in as_completed(future_to_file):
            test_file = future_to_file[future]
            try:
                test_file_path, return_code, stdout, stderr, duration = future.result()
                
                status = "✓ PASSED" if return_code == 0 else "✗ FAILED"
                print(f"\n[{status}] {test_file_path} ({duration:.1f}s)")
                
                if return_code == 0:
                    results["passed"].append(test_file_path)
                    # Show brief summary
                    if stdout:
                        # Extract pass/fail count from output
                        lines = stdout.split('\n')
                        for line in lines[-10:]:
                            if "passed" in line.lower() or "failed" in line.lower():
                                print(f"  {line.strip()}")
                else:
                    results["failed"].append((test_file_path, return_code, stderr))
                    # Show error summary
                    if stderr:
                        error_lines = stderr.split('\n')[:5]
                        for line in error_lines:
                            if line.strip():
                                print(f"  ERROR: {line.strip()}")
                
            except Exception as e:
                print(f"\n[✗ ERROR] {test_file}: {e}")
                results["failed"].append((test_file, 1, str(e)))
    
    total_duration = time.time() - start_time
    results["total_duration"] = total_duration
    
    # Print summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Total test files: {len(test_files)}")
    print(f"Passed: {len(results['passed'])}")
    print(f"Failed: {len(results['failed'])}")
    print(f"Total duration: {total_duration:.1f}s")
    
    if results["passed"]:
        print("\nPassed files:")
        for file in results["passed"]:
            print(f"  ✓ {file}")
    
    if results["failed"]:
        print("\nFailed files:")
        for item in results["failed"]:
            if isinstance(item, tuple):
                file, code, error = item
                print(f"  ✗ {file} (exit code: {code})")
            else:
                print(f"  ✗ {item}")
    
    return results


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Run test files in parallel with nested parallel execution"
    )
    parser.add_argument(
        "test_files",
        nargs="*",
        help="Test files to run (default: all router comprehensive tests)"
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=None,
        help="Maximum number of test files to run in parallel (default: auto)"
    )
    parser.add_argument(
        "--file-workers",
        type=int,
        default=None,
        help="Number of workers per test file (default: auto for pytest-xdist)"
    )
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Run with coverage reporting"
    )
    
    args = parser.parse_args()
    
    # Determine test files to run
    if args.test_files:
        test_files = args.test_files
    else:
        test_files = DEFAULT_TEST_FILES
    
    # Verify test files exist
    valid_files = []
    for test_file in test_files:
        file_path = PROJECT_ROOT / test_file
        if file_path.exists():
            valid_files.append(test_file)
        else:
            print(f"Warning: Test file not found: {test_file}", file=sys.stderr)
    
    if not valid_files:
        print("Error: No valid test files found", file=sys.stderr)
        return 1
    
    # Run tests
    results = run_tests_parallel(
        valid_files,
        max_workers=args.max_workers,
        file_workers=args.file_workers
    )
    
    # Return appropriate exit code
    return 0 if len(results["failed"]) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

