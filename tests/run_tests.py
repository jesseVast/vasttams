#!/usr/bin/env python3
"""
TAMS Test Runner

This script provides an easy way to run different types of tests:
- Unit tests (fast, mocked)
- Integration tests (slower, real services)
- All tests
- Specific test categories
"""

import argparse
import subprocess
import sys
import os
from pathlib import Path

def run_command(cmd, description):
    """Run a command and handle errors gracefully"""
    print(f"\n🚀 {description}")
    print(f"Command: {' '.join(cmd)}")
    print("-" * 60)
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=False)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed with exit code {e.returncode}")
        return False
    except KeyboardInterrupt:
        print(f"\n⏹️  {description} interrupted by user")
        return False

def main():
    parser = argparse.ArgumentParser(description="TAMS Test Runner")
    parser.add_argument(
        "--type", 
        choices=["unit", "integration", "all"], 
        default="unit",
        help="Type of tests to run (default: unit)"
    )
    parser.add_argument(
        "--category",
        choices=["vastdb", "s3", "auth", "api", "performance"],
        help="Specific test category to run"
    )
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Run with coverage reporting"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose output"
    )
    parser.add_argument(
        "--pattern",
        help="Run tests matching pattern (e.g., 'test_vastdbmanager')"
    )
    
    args = parser.parse_args()
    
    # Determine test path based on type
    if args.type == "unit":
        test_path = "mock_tests"
        description = "Unit Tests (Mocked)"
    elif args.type == "integration":
        test_path = "real_tests"
        description = "Integration Tests (Real Services)"
    else:  # all
        test_path = "."
        description = "All Tests"
    
    # Build pytest command
    cmd = ["python", "-m", "pytest", test_path]
    
    # Add options
    if args.verbose:
        cmd.append("-v")
    
    if args.coverage:
        cmd.extend(["--cov=app", "--cov-report=html", "--cov-report=term"])
    
    if args.category:
        cmd.extend(["-m", args.category])
    
    if args.pattern:
        cmd.extend(["-k", args.pattern])
    
    # Add common options
    cmd.extend(["--tb=short", "--disable-warnings"])
    
    # Run the tests
    success = run_command(cmd, description)
    
    if success:
        print(f"\n🎉 {description} completed successfully!")
        if args.coverage:
            print("📊 Coverage report generated in htmlcov/")
    else:
        print(f"\n💥 {description} failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
