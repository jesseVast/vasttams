#!/usr/bin/env python3
"""
Database Integration Tests for Flow Segments

Tests that interact with a running TAMS server and real VAST database.
"""

import pytest
import sys
import requests
from pathlib import Path
import time
import uuid

# Add src to path for imports
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from vasttams.core.config import get_settings

import logging
logger = logging.getLogger(__name__)

# Get settings for API base URL
settings = get_settings()
BASE_URL = f"http://{settings.host}:{settings.port}"


@pytest.fixture(scope="module")
def api_available():
    """Check if API server is running"""
    try:
        response = requests.get(f"{BASE_URL}/", timeout=2)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        pytest.skip("API server not running. Start server with: python run.py")


@pytest.fixture
def test_flow_and_source():
    """Create a test flow and source for segment testing"""
    source_id = str(uuid.uuid4())
    flow_id = str(uuid.uuid4())
    
    # Create source
    source_data = {
        "id": source_id,
        "format": "urn:x-nmos:format:video",
        "label": f"Test Source {source_id[:8]}"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/sources", json=source_data)
        if response.status_code != 201:
            pytest.skip(f"Failed to create test source: {response.text}")
        
        # Create flow
        flow_data = {
            "id": flow_id,
            "source_id": source_id,
            "format": "urn:x-nmos:format:video",
            "codec": "video/H264",
            "label": f"Test Flow {flow_id[:8]}",
            "essence_parameters": {
                "frame_width": 1920,
                "frame_height": 1080,
                "frame_rate": {
                    "numerator": 25,
                    "denominator": 1
                },
                "interlace_mode": "progressive",
                "transfer_characteristic": "ITU-R BT.709"
            }
        }
        
        response = requests.post(f"{BASE_URL}/flows", json=flow_data)
        if response.status_code != 201:
            pytest.skip(f"Failed to create test flow: {response.text}")
        
        yield {"flow_id": flow_id, "source_id": source_id}
        
    finally:
        # Cleanup
        requests.delete(f"{BASE_URL}/flows/{flow_id}")
        requests.delete(f"{BASE_URL}/sources/{source_id}")


@pytest.mark.usefixtures("api_available")
class TestSegmentDatabaseIntegration:
    """Integration tests for Segments against real database"""
    
    def test_list_segments_from_database(self, api_available, test_flow_and_source):
        """Test listing segments for a flow per TAMS 8.0 spec"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_and_source["flow_id"]
        
        response = requests.get(f"{BASE_URL}/flows/{flow_id}/segments")
        assert response.status_code == 200
        
        # TAMS 8.0: segments endpoint returns a list
        segments = response.json()
        assert isinstance(segments, list)
    
    def test_filter_segments_by_timerange(self, api_available, test_flow_and_source):
        """Test filtering segments by timerange per TAMS 8.0"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_and_source["flow_id"]
        
        # Test with timerange filter
        response = requests.get(f"{BASE_URL}/flows/{flow_id}/segments?timerange=2020-01-01T00:00:00Z,2020-01-01T00:01:00Z")
        assert response.status_code == 200
        
        segments = response.json()
        assert isinstance(segments, list)


@pytest.mark.usefixtures("api_available")
class TestSegmentCRUD:
    """Test segment CRUD operations"""
    
    def test_create_segment_with_storage(self, api_available, test_flow_and_source):
        """Test creating a segment with storage allocation"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_and_source["flow_id"]
        
        # Request storage for the flow
        storage_request = {
            "duration": {
                "numerator": 4,
                "denominator": 1
            },
            "object_ids": []
        }
        
        response = requests.post(
            f"{BASE_URL}/flows/{flow_id}/storage",
            json=storage_request
        )
        
        if response.status_code in [200, 201]:
            storage = response.json()
            assert "urls" in storage or "storage_id" in storage
    
    def test_get_segment_details(self, api_available, test_flow_and_source):
        """Test getting detailed segment information per TAMS 8.0 spec"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_and_source["flow_id"]
        
        # First, list segments to get one to query
        response = requests.get(f"{BASE_URL}/flows/{flow_id}/segments")
        if response.status_code == 200:
            segments = response.json()
            assert isinstance(segments, list)
            
            if len(segments) > 0:
                # Verify segment structure per TAMS 8.0 spec
                segment = segments[0]
                assert "id" in segment
                # Segments should have timerange per spec
                if "timerange" in segment:
                    assert isinstance(segment["timerange"], dict)

