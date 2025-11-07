"""
Pytest plugin for test tracking

Integrates TestTracker with pytest to skip tests that haven't been affected by code changes.
"""

import pytest
import sys
from pathlib import Path

# Add tests directory to path for imports
tests_dir = Path(__file__).parent
sys.path.insert(0, str(tests_dir))

from test_tracker import get_tracker


def pytest_collection_modifyitems(config, items):
    """
    Modify test collection to skip tests that don't need to run
    
    This hook is called after test collection but before test execution.
    We mark tests that should be skipped with pytest.skip().
    """
    # Check if tracker is disabled via command line
    if config.getoption("--no-test-tracker", default=False):
        return
    
    tracker = get_tracker()
    skipped_count = 0
    
    for item in items:
        test_id = item.nodeid
        
        # Always run tests marked with @pytest.mark.always_run
        if item.get_closest_marker("always_run"):
            continue
        
        # Check if test should be run
        if not tracker.should_run_test(test_id):
            # Mark test to be skipped
            skip_marker = pytest.mark.skip(
                reason=f"Test passed previously and code hasn't changed"
            )
            item.add_marker(skip_marker)
            skipped_count += 1
    
    if skipped_count > 0:
        print(f"\n⏭️  Skipping {skipped_count} tests (passed previously, code unchanged)")


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """
    Record test results in tracker
    
    This hook runs after each test and records whether it passed or failed.
    """
    # Execute the test and get the result
    outcome = yield
    rep = outcome.get_result()
    
    # Skip tracking if disabled
    if hasattr(item.config.option, 'no_test_tracker') and item.config.option.no_test_tracker:
        return
    
    tracker = get_tracker()
    test_id = item.nodeid
    
    # Record test result
    if rep.when == "call":  # Only record on actual test execution, not setup/teardown
        if rep.outcome == "passed":
            tracker.record_test_passed(test_id)
        elif rep.outcome == "failed":
            error_msg = str(rep.longrepr) if hasattr(rep, 'longrepr') else ""
            tracker.record_test_failed(test_id, error_msg)


def pytest_sessionfinish(session, exitstatus):
    """Print statistics at end of test session"""
    # Skip if tracker is disabled
    if hasattr(session.config.option, 'no_test_tracker') and session.config.option.no_test_tracker:
        return
    
    tracker = get_tracker()
    stats = tracker.get_stats()
    
    if stats['total_tracked'] > 0:
        print(f"\n📊 Test Tracker Stats:")
        print(f"   Passed (cached): {stats['total_passed']}")
        print(f"   Failed (tracked): {stats['total_failed']}")
        print(f"   Total tracked: {stats['total_tracked']}")


def pytest_configure(config):
    """Register custom markers and command line options"""
    config.addinivalue_line(
        "markers", "always_run: Always run this test, even if code hasn't changed"
    )


def pytest_addoption(parser):
    """Add command line options for test tracker"""
    parser.addoption(
        "--no-test-tracker",
        action="store_true",
        default=False,
        help="Disable test tracking (run all tests regardless of cache)"
    )

