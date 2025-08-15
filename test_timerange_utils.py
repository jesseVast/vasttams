#!/usr/bin/env python3
"""
Simple test script for timerange utilities
"""

import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

try:
    from core.timerange_utils import (
    TimerangeGenerator, 
    get_default_timerange, 
    get_storage_timerange,
    get_short_timerange,
    get_medium_timerange,
        get_long_timerange
    )
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("This is expected when running outside the app context")
    sys.exit(1)

def test_timerange_utilities():
    """Test the timerange utility functions"""
    print("🧪 Testing Timerange Utilities")
    print("=" * 50)
    
    # Test default timerange
    print(f"Default timerange (5 min): {get_default_timerange()}")
    print(f"Storage timerange (5 min): {get_storage_timerange()}")
    print(f"Short timerange (1 min): {get_short_timerange()}")
    print(f"Medium timerange (5 min): {get_medium_timerange()}")
    print(f"Long timerange (15 min): {get_long_timerange()}")
    
    # Test custom durations
    print(f"\nCustom durations:")
    print(f"10 seconds: {TimerangeGenerator.generate_default_timerange(10)}")
    print(f"2 minutes: {TimerangeGenerator.generate_default_timerange(120)}")
    print(f"1 hour: {TimerangeGenerator.generate_default_timerange(3600)}")
    
    # Test timerange parsing
    test_timerange = "[00:00:00.000,05:00.000)"
    print(f"\nParsing timerange: {test_timerange}")
    start_sec, end_sec = TimerangeGenerator.parse_timerange(test_timerange)
    print(f"Start: {start_sec}s, End: {end_sec}s, Duration: {end_sec - start_sec}s")
    
    # Test validation
    print(f"\nValidation tests:")
    print(f"Valid timerange: {TimerangeGenerator.is_valid_timerange(test_timerange)}")
    print(f"Invalid timerange: {TimerangeGenerator.is_valid_timerange('invalid')}")
    
    print("\n✅ All timerange utility tests completed!")

if __name__ == "__main__":
    test_timerange_utilities()
