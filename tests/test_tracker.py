#!/usr/bin/env python3
"""
Test Tracking System

Tracks which tests have passed and only re-runs them when the code they test has changed.
This significantly speeds up test runs by skipping tests that haven't been affected by code changes.
"""

import json
import os
import hashlib
from pathlib import Path
from typing import Dict, Set, List, Optional
from datetime import datetime, timezone


class TestTracker:
    """Tracks test results and determines which tests need to run based on code changes"""
    
    def __init__(self, cache_file: Optional[str] = None):
        """
        Initialize the test tracker
        
        Args:
            cache_file: Path to cache file (default: .pytest_cache/test_tracker.json)
        """
        if cache_file is None:
            cache_file = Path(__file__).parent.parent / ".pytest_cache" / "test_tracker.json"
        
        self.cache_file = Path(cache_file)
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Load existing cache
        self.cache = self._load_cache()
        
        # Map test files to source files they likely test
        self.test_to_source_map = self._build_test_source_map()
    
    def _load_cache(self) -> Dict:
        """Load test tracking cache from file"""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        
        return {
            "passed_tests": {},  # test_id -> {"timestamp": "...", "source_files": [...]}
            "failed_tests": {},  # test_id -> {"timestamp": "...", "last_error": "..."}
            "source_file_hashes": {}  # source_file -> hash of file content
        }
    
    def _save_cache(self):
        """Save test tracking cache to file"""
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(self.cache, f, indent=2)
        except Exception:
            pass
    
    def _build_test_source_map(self) -> Dict[str, List[str]]:
        """
        Build a map of test files to source files they likely test
        
        Returns:
            Dict mapping test file paths to list of source file paths
        """
        test_dir = Path(__file__).parent
        src_dir = test_dir.parent / "src"
        
        mapping = {}
        
        # Map test files to source files based on naming conventions
        for test_file in test_dir.rglob("test_*.py"):
            test_path = str(test_file.relative_to(test_dir))
            source_files = []
            
            # Extract module name from test file
            # e.g., tests/flows/test_router_comprehensive.py -> src/vasttams/flows/router.py
            parts = test_path.replace("test_", "").replace(".py", "").split("/")
            
            if len(parts) >= 2:
                module = parts[0]  # e.g., "flows"
                test_type = parts[-1]  # e.g., "router_comprehensive"
                
                # Map to likely source files
                if "router" in test_type:
                    source_files.append(f"src/vasttams/{module}/router.py")
                elif "service" in test_type:
                    source_files.append(f"src/vasttams/{module}/service.py")
                elif "models" in test_type:
                    source_files.append(f"src/vasttams/{module}/models.py")
                elif "schemas" in test_type:
                    source_files.append(f"src/vasttams/{module}/schemas.py")
                elif module == "auth":
                    if "rbac" in test_type:
                        source_files.append("src/vasttams/auth/rbac.py")
                    elif "providers" in test_type:
                        source_files.append("src/vasttams/auth/providers/")
                    elif "middleware" in test_type or "dependencies" in test_type:
                        source_files.append("src/vasttams/auth/middleware.py")
                        source_files.append("src/vasttams/auth/dependencies.py")
                elif module == "core":
                    if "errors" in test_type:
                        source_files.append("src/vasttams/core/tams_errors.py")
                    elif "logging" in test_type:
                        source_files.append("src/vasttams/core/tams_logging.py")
                        source_files.append("src/vasttams/core/simple_logging.py")
                    elif "responses" in test_type:
                        source_files.append("src/vasttams/common/responses.py")
                    elif "timerange" in test_type:
                        source_files.append("src/vasttams/core/timerange_utils.py")
                elif module == "common":
                    if "storage" in test_type:
                        source_files.append("src/vasttams/common/storage/")
                    elif "tags" in test_type:
                        source_files.append("src/vasttams/common/tags/")
                elif module == "main":
                    source_files.append("src/vasttams/main.py")
                elif module == "looprecorder":
                    source_files.append("src/vasttams/looprecorder/manager.py")
            
            # Also include the test file itself (if test changes, re-run it)
            source_files.append(str(test_file))
            
            mapping[str(test_file)] = source_files
        
        return mapping
    
    def _get_file_hash(self, file_path: Path) -> Optional[str]:
        """Get hash of file content"""
        if not file_path.exists():
            return None
        
        try:
            with open(file_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception:
            return None
    
    def _get_source_files_for_test(self, test_id: str) -> List[str]:
        """Get list of source files that a test likely depends on"""
        # Extract test file from test_id
        # test_id format: tests/flows/test_router_comprehensive.py::TestClass::test_method
        test_file = test_id.split("::")[0]
        
        # Get mapped source files
        source_files = self.test_to_source_map.get(test_file, [])
        
        # Also check for any files in the same directory structure
        test_path = Path(test_file)
        if test_path.exists():
            src_dir = test_path.parent.parent / "src"
            if src_dir.exists():
                # Add all Python files in corresponding src directory
                module = test_path.parent.name
                module_src = src_dir / "vasttams" / module
                if module_src.exists():
                    for py_file in module_src.rglob("*.py"):
                        source_files.append(str(py_file))
        
        return list(set(source_files))  # Remove duplicates
    
    def should_run_test(self, test_id: str) -> bool:
        """
        Determine if a test should be run based on cache and code changes
        
        Args:
            test_id: Full test identifier (e.g., "tests/flows/test_router.py::TestClass::test_method")
            
        Returns:
            True if test should be run, False if it can be skipped
        """
        # Always run if test has never been seen
        if test_id not in self.cache["passed_tests"] and test_id not in self.cache["failed_tests"]:
            return True
        
        # Always run if test previously failed
        if test_id in self.cache["failed_tests"]:
            return True
        
        # Check if any source files have changed
        source_files = self._get_source_files_for_test(test_id)
        test_info = self.cache["passed_tests"].get(test_id, {})
        cached_source_files = test_info.get("source_files", [])
        
        # Check if any source file has changed
        for source_file in source_files:
            source_path = Path(source_file)
            
            # Handle directory paths
            if source_path.is_dir():
                for py_file in source_path.rglob("*.py"):
                    if self._has_file_changed(str(py_file)):
                        return True
            elif source_path.exists():
                if self._has_file_changed(str(source_path)):
                    return True
        
        # Check if test file itself changed
        test_file = test_id.split("::")[0]
        if self._has_file_changed(test_file):
            return True
        
        # All source files unchanged, skip test
        return False
    
    def _has_file_changed(self, file_path: str) -> bool:
        """Check if a file has changed since last cache update"""
        path = Path(file_path)
        if not path.exists():
            return False
        
        current_hash = self._get_file_hash(path)
        cached_hash = self.cache["source_file_hashes"].get(file_path)
        
        if cached_hash is None or current_hash != cached_hash:
            # Update hash
            if current_hash:
                self.cache["source_file_hashes"][file_path] = current_hash
            return True
        
        return False
    
    def record_test_passed(self, test_id: str):
        """Record that a test passed"""
        source_files = self._get_source_files_for_test(test_id)
        
        # Update source file hashes
        for source_file in source_files:
            source_path = Path(source_file)
            if source_path.is_dir():
                for py_file in source_path.rglob("*.py"):
                    file_hash = self._get_file_hash(py_file)
                    if file_hash:
                        self.cache["source_file_hashes"][str(py_file)] = file_hash
            elif source_path.exists():
                file_hash = self._get_file_hash(source_path)
                if file_hash:
                    self.cache["source_file_hashes"][source_file] = file_hash
        
        # Record test as passed
        self.cache["passed_tests"][test_id] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source_files": source_files
        }
        
        # Remove from failed tests if it was there
        if test_id in self.cache["failed_tests"]:
            del self.cache["failed_tests"][test_id]
        
        self._save_cache()
    
    def record_test_failed(self, test_id: str, error: str = ""):
        """Record that a test failed"""
        self.cache["failed_tests"][test_id] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "last_error": error[:500]  # Truncate long errors
        }
        
        # Remove from passed tests if it was there
        if test_id in self.cache["passed_tests"]:
            del self.cache["passed_tests"][test_id]
        
        self._save_cache()
    
    def get_stats(self) -> Dict:
        """Get statistics about tracked tests"""
        return {
            "total_passed": len(self.cache["passed_tests"]),
            "total_failed": len(self.cache["failed_tests"]),
            "total_tracked": len(self.cache["passed_tests"]) + len(self.cache["failed_tests"])
        }
    
    def clear_cache(self):
        """Clear all cached test results"""
        self.cache = {
            "passed_tests": {},
            "failed_tests": {},
            "source_file_hashes": {}
        }
        self._save_cache()


# Global tracker instance
_tracker = None


def get_tracker() -> TestTracker:
    """Get or create global test tracker instance"""
    global _tracker
    if _tracker is None:
        _tracker = TestTracker()
    return _tracker


# ============================================================================
# Pytest Plugin Integration
# ============================================================================

try:
    import pytest
    _pytest_available = True
except ImportError:
    _pytest_available = False


if _pytest_available:
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

