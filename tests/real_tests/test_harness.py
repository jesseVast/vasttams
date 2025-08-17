#!/usr/bin/env python3
"""
Centralized Test Harness for TAMS Real Tests

This module provides a unified testing environment with:
- Centralized environment setup
- Consistent fixtures and configuration
- Proper error handling and timeouts
- Shared test data and utilities
"""

import os
import pytest
import uuid
from datetime import datetime, timezone
from unittest.mock import Mock
from typing import Dict, Any, Optional, TYPE_CHECKING

# Import models after environment is set
from app.models.models import Source, VideoFlow, FlowSegment, TimeRange

# Type checking imports
if TYPE_CHECKING:
    from app.storage.s3_store import S3Store


class TestHarness:
    """Centralized test harness providing consistent setup and configuration"""
    
    def __init__(self):
        """Initialize the test harness with environment setup"""
        self._setup_environment()
        self._setup_test_data()
    
    def _setup_environment(self):
        """Set up environment variables for real testing"""
        # Set VAST Database settings (from docker-compose.yml)
        # Note: Application uses TAMS_ prefix for environment variables
        os.environ["TAMS_VAST_ENDPOINT"] = "http://172.200.204.90"
        os.environ["TAMS_VAST_ACCESS_KEY"] = "SRSPW0DQT9T70Y787U68"
        os.environ["TAMS_VAST_SECRET_KEY"] = "WkKLxvG7YkAdSMuHjFsZG5/BhDk9Ou7BS1mDQGnr"
        os.environ["TAMS_VAST_BUCKET"] = "jthaloor-db"
        os.environ["TAMS_VAST_SCHEMA"] = "tams7"
        
        # Set S3 settings (from docker-compose.yml)
        os.environ["TAMS_S3_ENDPOINT_URL"] = "http://172.200.204.91"
        os.environ["TAMS_S3_ACCESS_KEY_ID"] = "SRSPW0DQT9T70Y787U68"
        os.environ["TAMS_S3_SECRET_ACCESS_KEY"] = "WkKLxvG7YkAdSMuHjFsZG5/BhDk9Ou7BS1mDQGnr"
        os.environ["TAMS_S3_BUCKET_NAME"] = "jthaloor-s3"
        os.environ["TAMS_S3_USE_SSL"] = "false"
        
        # Set server settings
        os.environ["HOST"] = "0.0.0.0"
        os.environ["PORT"] = "8000"
        os.environ["ENVIRONMENT"] = "development"
        os.environ["LOG_LEVEL"] = "DEBUG"
        
        print("🔧 Test harness environment configured:")
        print(f"   VAST: {os.environ['TAMS_VAST_ENDPOINT']}")
        print(f"   S3: {os.environ['TAMS_S3_ENDPOINT_URL']}")
        print(f"   Server: {os.environ['HOST']}:{os.environ['PORT']}")
    
    def _setup_test_data(self):
        """Set up common test data structures"""
        self.test_source_id = uuid.uuid4()
        self.test_flow_id = uuid.uuid4()
        self.test_segment_id = str(uuid.uuid4())
    
    def get_vast_endpoint(self) -> str:
        """Get VAST endpoint for testing"""
        return os.environ["TAMS_VAST_ENDPOINT"]
    
    def get_s3_endpoint(self) -> str:
        """Get S3 endpoint for testing"""
        return os.environ["TAMS_S3_ENDPOINT_URL"]
    
    def get_vast_credentials(self) -> Dict[str, str]:
        """Get VAST credentials for testing"""
        return {
            "access_key": os.environ["TAMS_VAST_ACCESS_KEY"],
            "secret_key": os.environ["TAMS_VAST_SECRET_KEY"],
            "bucket": os.environ["TAMS_VAST_BUCKET"],
            "schema": os.environ["TAMS_VAST_SCHEMA"]
        }
    
    def get_s3_credentials(self) -> Dict[str, str]:
        """Get S3 credentials for testing"""
        return {
            "access_key_id": os.environ["TAMS_S3_ACCESS_KEY_ID"],
            "secret_access_key": os.environ["TAMS_S3_SECRET_ACCESS_KEY"],
            "bucket_name": os.environ["TAMS_S3_BUCKET_NAME"],
            "use_ssl": os.environ["TAMS_S3_USE_SSL"]
        }
    
    def get_s3_store(self) -> Optional['S3Store']:
        """Get S3Store instance for testing"""
        try:
            from app.storage.s3_store import S3Store
            store = S3Store(
                endpoint_url=self.get_s3_endpoint(),
                access_key_id=os.environ["TAMS_S3_ACCESS_KEY_ID"],
                secret_access_key=os.environ["TAMS_S3_SECRET_ACCESS_KEY"],
                bucket_name=os.environ["TAMS_S3_BUCKET_NAME"],
                use_ssl=os.environ["TAMS_S3_USE_SSL"] == "true"
            )
            return store
        except Exception as e:
            print(f"⚠️  S3 store not available: {e}")
            return None
    
    def is_s3_available(self) -> bool:
        """Check if S3 is available for testing"""
        try:
            store = self.get_s3_store()
            return store is not None
        except:
            return False
    
    def create_sample_source(self, **kwargs) -> Source:
        """Create a sample source with consistent data"""
        defaults = {
            "id": self.test_source_id,
            "format": "urn:x-nmos:format:video",
            "label": "Test Source",
            "description": "A test source for testing"
        }
        defaults.update(kwargs)
        return Source(**defaults)
    
    def create_sample_video_flow(self, **kwargs) -> VideoFlow:
        """Create a sample video flow with consistent data"""
        defaults = {
            "id": self.test_flow_id,
            "source_id": self.test_source_id,
            "label": "Test Video Flow",
            "description": "A test video flow for testing",
            "codec": "video/h264",
            "frame_width": 1920,
            "frame_height": 1080,
            "frame_rate": "25/1"
        }
        defaults.update(kwargs)
        return VideoFlow(**defaults)
    
    def create_sample_flow_segment(self, **kwargs) -> FlowSegment:
        """Create a sample flow segment with consistent data"""
        defaults = {
            "object_id": self.test_segment_id,
            "timerange": "0:0_3600:0",  # Correct TimeRange format: 1 hour range
            "sample_offset": 0,
            "sample_count": 90000,
            "key_frame_count": 3600
        }
        defaults.update(kwargs)
        return FlowSegment(**defaults)
    
    def create_mock_vast_store(self) -> Mock:
        """Create a mock VAST store for API testing"""
        mock_store = Mock()
        mock_store.get_sources = Mock(return_value=[])
        mock_store.get_source = Mock(return_value=None)
        mock_store.create_source = Mock(return_value=True)
        mock_store.delete_source = Mock(return_value=True)
        return mock_store
    
    def get_test_config(self) -> Dict[str, Any]:
        """Get complete test configuration as a dictionary"""
        return {
            "vast_endpoint": self.get_vast_endpoint(),
            "s3_endpoint": self.get_s3_endpoint(),
            "vast_credentials": self.get_vast_credentials(),
            "s3_credentials": self.get_s3_credentials(),
            "server_host": os.environ["HOST"],
            "server_port": os.environ["PORT"],
            "test_source_id": str(self.test_source_id),
            "test_flow_id": str(self.test_flow_id),
            "test_segment_id": self.test_segment_id
        }


# Global test harness instance
test_harness = TestHarness()


# Pytest fixtures that use the harness
@pytest.fixture(scope="session")
def harness():
    """Provide the test harness to all tests"""
    return test_harness


@pytest.fixture(scope="session")
def test_config(harness):
    """Provide test configuration to all tests"""
    return harness.get_test_config()


@pytest.fixture
def sample_source(harness):
    """Provide a sample source for testing"""
    return harness.create_sample_source()


@pytest.fixture
def sample_video_flow(harness):
    """Provide a sample video flow for testing"""
    return harness.create_sample_video_flow()


@pytest.fixture
def sample_flow_segment(harness):
    """Provide a sample flow segment for testing"""
    return harness.create_sample_flow_segment()


@pytest.fixture
def mock_vast_store(harness):
    """Provide a mock VAST store for API testing"""
    return harness.create_mock_vast_store()


@pytest.fixture
def vast_endpoint(harness):
    """Provide VAST endpoint for testing"""
    return harness.get_vast_endpoint()


@pytest.fixture
def s3_endpoint(harness):
    """Provide S3 endpoint for testing"""
    return harness.get_s3_endpoint()


@pytest.fixture
def vast_credentials(harness):
    """Provide VAST credentials for testing"""
    return harness.get_vast_credentials()


@pytest.fixture
def s3_credentials(harness):
    """Provide S3 credentials for testing"""
    return harness.get_s3_credentials()


# Import this module to automatically set up the environment
if __name__ == "__main__":
    print("Test harness initialized")
    print(f"Test config: {test_harness.get_test_config()}")
