#!/usr/bin/env python3
"""
Comprehensive TAMS API Test Runner

This script runs all endpoint tests in a organized manner:
- Core service tests
- Sources tests
- Flows tests
- Segments tests
- Objects tests
- Analytics tests
- Webhooks tests
- Deletion requests tests
"""

import sys
import time
from datetime import datetime
from test_utils import print_section, cleanup_test_data

def run_test_module(module_name, test_function):
    """Run a test module and handle results"""
    print_section(f"RUNNING {module_name.upper()} TESTS")
    start_time = time.time()
    
    try:
        test_function()
        end_time = time.time()
        duration = end_time - start_time
        print(f"✅ {module_name.title()} tests completed successfully in {duration:.2f} seconds")
        return True
    except Exception as e:
        end_time = time.time()
        duration = end_time - start_time
        print(f"❌ {module_name.title()} tests failed after {duration:.2f} seconds: {e}")
        return False

def run_all_tests():
    """Run all TAMS API endpoint tests"""
    print("🚀 Starting Comprehensive TAMS API Endpoint Tests")
    print(f"⏰ Start Time: {datetime.now().isoformat()}")
    print("=" * 80)
    
    # Import test modules
    try:
        from test_core_service import run_all_core_service_tests
        from test_sources import run_all_sources_tests
        from test_flows import run_all_flows_tests
        from test_segments import run_all_segments_tests
        from test_objects import run_all_objects_tests
        from test_analytics import run_all_analytics_tests
        from test_webhooks import run_all_webhooks_tests
        from test_deletion_requests import run_all_deletion_requests_tests
    except ImportError as e:
        print(f"❌ Failed to import test modules: {e}")
        return False
    
    # Test modules and their functions
    test_modules = [
        ("Core Service", run_all_core_service_tests),
        ("Sources", run_all_sources_tests),
        ("Flows", run_all_flows_tests),
        ("Segments", run_all_segments_tests),
        ("Objects", run_all_objects_tests),
        ("Analytics", run_all_analytics_tests),
        ("Webhooks", run_all_webhooks_tests),
        ("Deletion Requests", run_all_deletion_requests_tests)
    ]
    
    # Run all tests
    results = []
    total_start_time = time.time()
    
    for module_name, test_function in test_modules:
        success = run_test_module(module_name, test_function)
        results.append((module_name, success))
        
        # Clean up after each module
        cleanup_test_data()
        
        # Small delay between modules
        time.sleep(1)
    
    total_end_time = time.time()
    total_duration = total_end_time - total_start_time
    
    # Print summary
    print_section("COMPREHENSIVE TEST SUMMARY")
    print(f"⏰ Total Duration: {total_duration:.2f} seconds")
    print(f"📊 Test Results:")
    
    passed = 0
    failed = 0
    
    for module_name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"   {module_name:20} {status}")
        if success:
            passed += 1
        else:
            failed += 1
    
    print(f"\n📈 Summary: {passed} passed, {failed} failed out of {len(results)} test modules")
    
    if failed == 0:
        print("🎉 All test modules passed successfully!")
        return True
    else:
        print(f"⚠️  {failed} test module(s) failed. Check the output above for details.")
        return False

def run_specific_tests(module_names):
    """Run specific test modules"""
    print(f"🚀 Running Specific TAMS API Tests: {', '.join(module_names)}")
    print(f"⏰ Start Time: {datetime.now().isoformat()}")
    print("=" * 80)
    
    # Import test modules
    try:
        from test_core_service import run_all_core_service_tests
        from test_sources import run_all_sources_tests
        from test_flows import run_all_flows_tests
        from test_segments import run_all_segments_tests
        from test_objects import run_all_objects_tests
        from test_analytics import run_all_analytics_tests
        from test_webhooks import run_all_webhooks_tests
        from test_deletion_requests import run_all_deletion_requests_tests
    except ImportError as e:
        print(f"❌ Failed to import test modules: {e}")
        return False
    
    # Map module names to functions
    module_map = {
        "core": ("Core Service", run_all_core_service_tests),
        "sources": ("Sources", run_all_sources_tests),
        "flows": ("Flows", run_all_flows_tests),
        "segments": ("Segments", run_all_segments_tests),
        "objects": ("Objects", run_all_objects_tests),
        "analytics": ("Analytics", run_all_analytics_tests),
        "webhooks": ("Webhooks", run_all_webhooks_tests),
        "deletion": ("Deletion Requests", run_all_deletion_requests_tests)
    }
    
    # Run specified tests
    results = []
    total_start_time = time.time()
    
    for module_name in module_names:
        if module_name.lower() in module_map:
            display_name, test_function = module_map[module_name.lower()]
            success = run_test_module(display_name, test_function)
            results.append((display_name, success))
            
            # Clean up after each module
            cleanup_test_data()
            
            # Small delay between modules
            time.sleep(1)
        else:
            print(f"⚠️  Unknown module: {module_name}")
            results.append((module_name, False))
    
    total_end_time = time.time()
    total_duration = total_end_time - total_start_time
    
    # Print summary
    print_section("SPECIFIC TEST SUMMARY")
    print(f"⏰ Total Duration: {total_duration:.2f} seconds")
    print(f"📊 Test Results:")
    
    passed = 0
    failed = 0
    
    for module_name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"   {module_name:20} {status}")
        if success:
            passed += 1
        else:
            failed += 1
    
    print(f"\n📈 Summary: {passed} passed, {failed} failed out of {len(results)} test modules")
    
    if failed == 0:
        print("🎉 All specified test modules passed successfully!")
        return True
    else:
        print(f"⚠️  {failed} test module(s) failed. Check the output above for details.")
        return False

def main():
    """Main entry point"""
    if len(sys.argv) > 1:
        # Run specific modules
        module_names = sys.argv[1:]
        success = run_specific_tests(module_names)
    else:
        # Run all tests
        success = run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
