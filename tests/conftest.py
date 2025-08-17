"""
Pytest Configuration for TAMS API Tests

This file provides global pytest configuration and fixtures that are
automatically available to all tests in the test suite.
"""

import pytest
import os
import sys

# Add the app directory to the Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import the centralized test harness
from tests.real_tests.test_harness import test_harness


# Global test configuration
def pytest_configure(config):
    """Configure pytest with test-specific settings"""
    # Add test markers
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests as slow running"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add default markers"""
    for item in items:
        # Add default markers based on test location
        if "mock_tests" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "real_tests" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        
        # Add slow marker for tests that might take time
        if "stress" in str(item.fspath) or "performance" in str(item.fspath):
            item.add_marker(pytest.mark.slow)


# Environment variable overrides for testing
@pytest.fixture(autouse=True)
def override_env_vars():
    """Override environment variables for testing"""
    env_overrides = {
        'VAST_ENDPOINT': 'http://172.200.204.90',
        'VAST_ACCESS_KEY': 'SRSPW0DQT9T70Y787U68',
        'VAST_SECRET_KEY': 'WkKLxvG7YkAdSMuHjFsZG5/BhDk9Ou7BS1mDQGnr',
        'VAST_BUCKET': 'jthaloor-db',
        'VAST_SCHEMA': 'tams7',
        'S3_ENDPOINT_URL': 'http://172.200.204.91',
        'S3_ACCESS_KEY_ID': 'SRSPW0DQT9T70Y787U68',
        'S3_SECRET_ACCESS_KEY': 'WkKLxvG7YkAdSMuHjFsZG5/BhDk9Ou7BS1mDQGnr',
        'S3_BUCKET_NAME': 'jthaloor-s3',
        'S3_USE_SSL': 'false',
        'HOST': '0.0.0.0',
        'PORT': '8000',
        'ENVIRONMENT': 'development',
        'LOG_LEVEL': 'DEBUG',
    }
    
    # The test harness already sets up the environment with TAMS_ prefix
    # This fixture is kept for backward compatibility but uses the harness
    return test_harness.get_test_config()
