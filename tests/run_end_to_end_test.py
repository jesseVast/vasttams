#!/usr/bin/env python3
"""
End-to-End Workflow Test Runner

This script runs the comprehensive end-to-end workflow test for TAMS API.
It tests the complete lifecycle including dependency management and proper deletion order.

Usage:
    python run_end_to_end_test.py [options]

Options:
    --clean-db        Clean database before running test
    --verbose         Verbose output
    --help            Show this help message
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path


def clean_database():
    """Clean the database before running the end-to-end test"""
    print("🧹 Cleaning database before end-to-end test...")
    
    try:
        # Run the database cleanup script
        result = subprocess.run([
            "/Users/jesse.thaloor/Developer/python/bbctams/bin/python", 
            "tests/drop_all_tables.py"
        ], cwd=Path(__file__).parent.parent, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Database cleaned successfully")
            return True
        else:
            print(f"❌ Database cleanup failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Error during database cleanup: {e}")
        return False


def run_end_to_end_test(options):
    """Run the end-to-end workflow test"""
    print("🚀 Running TAMS End-to-End Workflow Test")
    print("=" * 60)
    
    # Check if we're in the right directory
    if not os.path.exists("app") or not os.path.exists("tests"):
        print("❌ Please run this script from the project root directory")
        return 1
    
    # Check if server is running
    print("🔍 Checking if TAMS server is running...")
    try:
        import requests
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            print("✅ TAMS server is running")
        else:
            print("❌ TAMS server is not responding correctly")
            return 1
    except ImportError:
        print("⚠️ requests module not available, skipping server check")
    except Exception as e:
        print(f"❌ Cannot connect to TAMS server: {e}")
        print("Please start the TAMS server first: python run.py")
        return 1
    
    # Clean database if requested
    if options.clean_db:
        print("⚠️  Database cleanup requested but skipping for this test")
        # if not clean_database():
        #     print("❌ Database cleanup failed, aborting test")
        #     return 1
    
    # Run the end-to-end test
    print("🧪 Starting end-to-end workflow test...")
    try:
        cmd = [
            "/Users/jesse.thaloor/Developer/python/bbctams/bin/python",
            "tests/real_tests/test_end_to_end_workflow.py"
        ]
        
        print(f"Running: {' '.join(cmd)}")
        print("-" * 80)
        
        result = subprocess.run(cmd, cwd=Path(__file__).parent.parent)
        return result.returncode
        
    except KeyboardInterrupt:
        print("\n❌ End-to-end test interrupted by user")
        return 1
    except Exception as e:
        print(f"❌ Error running end-to-end test: {e}")
        return 1


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Run TAMS End-to-End Workflow Test")
    parser.add_argument("--clean-db", action="store_true", help="Clean database before running test")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    # Print test information
    print("TAMS End-to-End Workflow Test")
    print("=" * 60)
    print("This test will:")
    print("1. Create source src-1")
    print("2. Create flow flow-1")
    print("3. Add 2 flow segments flow-seg-1, flow-seg-2")
    print("4. Test source deletion (should fail)")
    print("5. Create flow-2 using flow-seg-2")
    print("6. Test data retrieval for each flow")
    print("7. Test flow-2 deletion (should succeed)")
    print("8. Test segment deletion dependencies")
    print("9. Test proper cleanup order")
    print("10. Verify final state")
    print()
    
    if args.clean_db:
        print("⚠️ Database will be cleaned before test (all data will be lost)")
        response = input("Continue? (y/N): ")
        if response.lower() != 'y':
            print("Test cancelled")
            return 0
    
    # Run the test
    return run_end_to_end_test(args)


if __name__ == "__main__":
    sys.exit(main())
