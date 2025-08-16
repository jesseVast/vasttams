"""
Test Configuration for TAMS API Tests

This module provides test-specific configuration that overrides the production
database and S3 settings to use mock/test values, preventing real connections
during testing.
"""

import os
import tempfile
from unittest.mock import patch
from app.config import Settings, get_settings, update_settings


class TestSettings(Settings):
    """Test-specific settings that override production database connections"""
    
    def __init__(self, **kwargs):
        # Override with test values before calling parent
        test_kwargs = {
            # Use mock/local endpoints for testing
            "vast_endpoints": ["http://localhost:8080"],
            "vast_endpoint": "http://localhost:8080",
            "vast_access_key": "test-access-key",
            "vast_secret_key": "test-secret-key",
            "vast_bucket": "test-bucket",
            "vast_schema": "test-schema",
            
            # Use mock/local S3 for testing
            "s3_endpoint_url": "http://localhost:9000",
            "s3_access_key_id": "test-s3-access-key",
            "s3_secret_access_key": "test-s3-secret-key",
            "s3_bucket_name": "test-s3-bucket",
            "s3_use_ssl": False,
            
            # Test-specific settings
            "debug": True,
            "log_level": "DEBUG",
        }
        
        # Update with any additional test kwargs
        test_kwargs.update(kwargs)
        
        # Call parent with test settings
        super().__init__(**test_kwargs)


def get_test_settings() -> TestSettings:
    """Get test-specific settings"""
    return TestSettings()


def create_test_env_file():
    """Create a temporary .env file for testing"""
    env_content = """# Test Environment Configuration
# This file is created automatically for testing and should not be committed

# VAST Database Test Settings
VAST_ENDPOINTS=["http://localhost:8080"]
VAST_ENDPOINT=http://localhost:8080
VAST_ACCESS_KEY=test-access-key
VAST_SECRET_KEY=test-secret-key
VAST_BUCKET=test-bucket
VAST_SCHEMA=test-schema

# S3 Test Settings
S3_ENDPOINT_URL=http://localhost:9000
S3_ACCESS_KEY_ID=test-s3-access-key
S3_SECRET_ACCESS_KEY=test-s3-secret-key
S3_BUCKET_NAME=test-s3-bucket
S3_USE_SSL=false

# Test Settings
DEBUG=true
LOG_LEVEL=DEBUG
"""
    
    # Create temporary .env file
    temp_env = tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False)
    temp_env.write(env_content)
    temp_env.close()
    
    return temp_env.name


def setup_test_environment():
    """Set up test environment with mock settings"""
    # Create test .env file
    env_file_path = create_test_env_file()
    
    # Patch environment variables
    env_patches = {
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
    
    # Apply patches
    patches = []
    for key, value in env_patches.items():
        patch_obj = patch.dict(os.environ, {key: value})
        patches.append(patch_obj)
    
    return patches, env_file_path


def cleanup_test_environment(env_file_path: str):
    """Clean up test environment files"""
    try:
        if os.path.exists(env_file_path):
            os.unlink(env_file_path)
    except OSError:
        pass  # Ignore cleanup errors


# Context manager for test environment
class TestEnvironment:
    """Context manager for test environment setup and cleanup"""
    
    def __init__(self):
        self.patches = []
        self.env_file_path = None
    
    def __enter__(self):
        self.patches, self.env_file_path = setup_test_environment()
        for patch_obj in self.patches:
            patch_obj.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        for patch_obj in self.patches:
            patch_obj.stop()
        if self.env_file_path:
            cleanup_test_environment(self.env_file_path)


# Convenience function for tests
def with_test_environment(func):
    """Decorator to automatically set up test environment"""
    def wrapper(*args, **kwargs):
        with TestEnvironment():
            return func(*args, **kwargs)
    return wrapper


# Export test settings for direct use
test_settings = get_test_settings()
