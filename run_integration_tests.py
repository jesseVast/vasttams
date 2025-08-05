#!/usr/bin/env python3
"""
Integration test runner for TAMS API with real database.

This script runs comprehensive integration tests using the real VAST database
and S3 storage to verify all functionality works correctly in a production-like environment.
"""

import asyncio
import logging
import sys
import os
import subprocess
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_pytest_tests():
    """Run pytest integration tests."""
    logger.info("🧪 Running pytest integration tests...")
    
    # Get the tests directory
    tests_dir = Path(__file__).parent / "tests"
    
    # Run pytest with specific test files
    test_files = [
        "test_integration_real_db.py",
        "test_soft_delete.py::TestSoftDeleteIntegration",
        "test_vast_integration.py",
        "test_integration_api.py"
    ]
    
    results = []
    for test_file in test_files:
        test_path = tests_dir / test_file
        if test_path.exists():
            logger.info(f"Running tests in {test_file}...")
            try:
                result = subprocess.run([
                    sys.executable, "-m", "pytest", 
                    str(test_path), 
                    "-v", 
                    "--tb=short",
                    "--asyncio-mode=auto"
                ], capture_output=True, text=True, cwd=tests_dir)
                
                if result.returncode == 0:
                    logger.info(f"✅ {test_file} tests passed")
                    results.append((test_file, True, result.stdout))
                else:
                    logger.error(f"❌ {test_file} tests failed")
                    logger.error(f"STDOUT: {result.stdout}")
                    logger.error(f"STDERR: {result.stderr}")
                    results.append((test_file, False, result.stderr))
                    
            except Exception as e:
                logger.error(f"❌ Failed to run {test_file}: {e}")
                results.append((test_file, False, str(e)))
        else:
            logger.warning(f"⚠️ Test file {test_file} not found")
            results.append((test_file, False, "File not found"))
    
    return results

async def run_direct_integration_test():
    """Run the direct integration test."""
    logger.info("🧪 Running direct integration test...")
    
    try:
        # Import and run the direct integration test
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'tests'))
        from test_integration_real_db import run_integration_tests
        
        result = await run_integration_tests()
        return [("Direct Integration Test", result == 0, "Completed")]
        
    except Exception as e:
        logger.error(f"❌ Direct integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return [("Direct Integration Test", False, str(e))]

async def main():
    """Main test runner."""
    logger.info("🚀 Starting TAMS Integration Test Suite with Real Database")
    logger.info("=" * 60)
    
    # Check if we're in the right directory
    if not os.path.exists("app") or not os.path.exists("tests"):
        logger.error("❌ Please run this script from the project root directory")
        return 1
    
    # Check if required services are available
    logger.info("🔍 Checking service availability...")
    
    # Import settings to check configuration
    try:
        sys.path.insert(0, 'app')
        from config import get_settings
        settings = get_settings()
        
        logger.info(f"VAST Endpoint: {settings.vast_endpoint}")
        logger.info(f"S3 Endpoint: {settings.s3_endpoint_url}")
        logger.info(f"VAST Bucket: {settings.vast_bucket}")
        logger.info(f"S3 Bucket: {settings.s3_bucket_name}")
        
    except Exception as e:
        logger.error(f"❌ Failed to load settings: {e}")
        return 1
    
    logger.info("✅ Configuration loaded successfully")
    logger.info("=" * 60)
    
    # Run direct integration test
    logger.info("\n📋 Running Direct Integration Tests...")
    direct_results = await run_direct_integration_test()
    
    # Run pytest tests
    logger.info("\n📋 Running Pytest Integration Tests...")
    pytest_results = run_pytest_tests()
    
    # Combine results
    all_results = direct_results + pytest_results
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("📊 INTEGRATION TEST SUMMARY")
    logger.info("=" * 60)
    
    passed = 0
    failed = 0
    
    for test_name, success, details in all_results:
        if success:
            logger.info(f"✅ {test_name}: PASSED")
            passed += 1
        else:
            logger.error(f"❌ {test_name}: FAILED")
            logger.error(f"   Details: {details}")
            failed += 1
    
    logger.info("=" * 60)
    logger.info(f"Total Tests: {len(all_results)}")
    logger.info(f"Passed: {passed}")
    logger.info(f"Failed: {failed}")
    logger.info(f"Success Rate: {(passed / len(all_results) * 100):.1f}%" if all_results else "0%")
    
    if failed == 0:
        logger.info("\n🎉 All integration tests passed!")
        logger.info("✅ TAMS API is ready for production use with real database")
        return 0
    else:
        logger.error(f"\n❌ {failed} integration test(s) failed")
        logger.error("⚠️ Please review the failures before deploying to production")
        return 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("\n⚠️ Test run interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n❌ Test runner failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1) 