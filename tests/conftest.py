"""
Pytest Configuration for TAMS API Tests

This file provides global pytest configuration and fixtures that are
automatically available to all tests in the test suite.
"""

import pytest
import os
import sys
from unittest.mock import patch
from tests.test_config import TestEnvironment, setup_test_environment, cleanup_test_environment


# Add the app directory to the Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


@pytest.fixture(scope="session", autouse=True)
def setup_test_session():
    """Set up test session environment"""
    # Set up test environment for the entire test session
    patches, env_file_path = setup_test_environment()
    
    # Start all patches
    for patch_obj in patches:
        patch_obj.start()
    
    yield
    
    # Stop all patches and cleanup
    for patch_obj in patches:
        patch_obj.stop()
    cleanup_test_environment(env_file_path)


@pytest.fixture(autouse=True)
def setup_test_environment_fixture():
    """Set up test environment for each test"""
    with TestEnvironment():
        yield


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
        'VAST_ENDPOINTS': '["http://localhost:8080"]',
        'VAST_ENDPOINT': 'http://localhost:8080',
        'VAST_ACCESS_KEY': 'test-access-key',
        'VAST_SECRET_KEY': 'test-secret-key',
        'VAST_BUCKET': 'test-bucket',
        'VAST_SCHEMA': 'test-schema',
        'S3_ENDPOINT_URL': 'http://localhost:9000',
        'S3_ACCESS_KEY_ID': 'test-s3-access-key',
        'S3_SECRET_ACCESS_KEY': 'test-s3-secret-key',
        'S3_BUCKET_NAME': 'test-s3-bucket',
        'S3_USE_SSL': 'false',
        'DEBUG': 'true',
        'LOG_LEVEL': 'DEBUG',
    }
    
    # Apply overrides
    with patch.dict(os.environ, env_overrides):
        yield
