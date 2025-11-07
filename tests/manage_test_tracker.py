#!/usr/bin/env python3
"""
Utility script to manage the test tracker cache

Usage:
    python tests/manage_test_tracker.py clear    # Clear all cached test results
    python tests/manage_test_tracker.py stats    # Show statistics
    python tests/manage_test_tracker.py list     # List all tracked tests
"""

import sys
from pathlib import Path

# Add tests directory to path
sys.path.insert(0, str(Path(__file__).parent))

from test_tracker import get_tracker


def main():
    if len(sys.argv) < 2:
        print("Usage: python tests/manage_test_tracker.py [clear|stats|list]")
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
    
    else:
        print(f"Unknown command: {command}")
        print("Usage: python tests/manage_test_tracker.py [clear|stats|list]")
        sys.exit(1)


if __name__ == "__main__":
    main()

