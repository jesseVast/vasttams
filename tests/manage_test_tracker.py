#!/usr/bin/env python3
"""
Utility script to manage the test tracker cache

Usage:
    python tests/manage_test_tracker.py clear    # Clear all cached test results
    python tests/manage_test_tracker.py stats    # Show statistics
    python tests/manage_test_tracker.py list     # List all tracked tests
    python tests/manage_test_tracker.py failed   # List only failed tests
    python tests/manage_test_tracker.py run-failed  # Run only failed tests
"""

import sys
import subprocess
from pathlib import Path

# Add tests directory to path
sys.path.insert(0, str(Path(__file__).parent))

from test_tracker import get_tracker


def main():
    if len(sys.argv) < 2:
        print("Usage: python tests/manage_test_tracker.py [clear|stats|list|failed|run-failed]")
        sys.exit(1)
    
    command = sys.argv[1]
    tracker = get_tracker()
    
    if command == "clear":
        tracker.clear_cache()
        print("✅ Test tracker cache cleared")
    
    elif command == "stats":
        stats = tracker.get_stats()
        print(f"\n📊 Test Tracker Statistics:")
        print(f"   Passed (cached): {stats['total_passed']}")
        print(f"   Failed (tracked): {stats['total_failed']}")
        print(f"   Total tracked: {stats['total_tracked']}")
        print(f"\n   Cache file: {tracker.cache_file}")
    
    elif command == "list":
        cache = tracker.cache
        print(f"\n✅ Passed Tests ({len(cache['passed_tests'])}):")
        for test_id in sorted(cache['passed_tests'].keys()):
            info = cache['passed_tests'][test_id]
            print(f"   {test_id}")
            print(f"      Last passed: {info.get('timestamp', 'unknown')}")
        
        print(f"\n❌ Failed Tests ({len(cache['failed_tests'])}):")
        for test_id in sorted(cache['failed_tests'].keys()):
            info = cache['failed_tests'][test_id]
            print(f"   {test_id}")
            print(f"      Last failed: {info.get('timestamp', 'unknown')}")
    
    elif command == "failed":
        cache = tracker.cache
        failed_tests = sorted(cache['failed_tests'].keys())
        
        if not failed_tests:
            print("\n✅ No failed tests tracked. All tests are passing!")
            return
        
        print(f"\n❌ Failed Tests ({len(failed_tests)}):")
        for i, test_id in enumerate(failed_tests, 1):
            info = cache['failed_tests'][test_id]
            print(f"   {i}. {test_id}")
            print(f"      Last failed: {info.get('timestamp', 'unknown')}")
            if info.get('last_error'):
                error_preview = info['last_error'][:100].replace('\n', ' ')
                print(f"      Error: {error_preview}...")
    
    elif command == "run-failed":
        cache = tracker.cache
        failed_tests = sorted(cache['failed_tests'].keys())
        
        if not failed_tests:
            print("\n✅ No failed tests to run. All tests are passing!")
            return
        
        print(f"\n🔧 Running {len(failed_tests)} failed tests...")
        print("=" * 60)
        
        # Get Python binary from environment or use default
        python_bin = "/Users/jesse.thaloor/Developer/python/vasttams/bin/python"
        
        # Ensure test paths have 'tests/' prefix if they don't already
        test_paths = []
        for test_id in failed_tests:
            if not test_id.startswith('tests/'):
                test_paths.append(f"tests/{test_id}")
            else:
                test_paths.append(test_id)
        
        # Build pytest command with options for focused debugging
        # Use --tb=short for concise output, or --tb=long for full details
        # Remove -x to run all tests, add it back to stop on first failure
        cmd = [python_bin, "-m", "pytest", "-v", "--tb=short"] + test_paths
        
        try:
            result = subprocess.run(cmd, cwd=Path(__file__).parent.parent)
            sys.exit(result.returncode)
        except KeyboardInterrupt:
            print("\n\n⚠️  Test run interrupted by user")
            sys.exit(130)
        except Exception as e:
            print(f"\n❌ Error running tests: {e}")
            sys.exit(1)
    
    else:
        print(f"Unknown command: {command}")
        print("Usage: python tests/manage_test_tracker.py [clear|stats|list|failed|run-failed]")
        sys.exit(1)


if __name__ == "__main__":
    main()

