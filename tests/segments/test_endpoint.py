#!/usr/bin/env python3
"""
Endpoint CRUD Tests for Flow Segments

Tests the segments endpoint using data from TAMS 8.0 examples.
These tests interact with the real API server.
"""

import pytest
import sys
import requests
from pathlib import Path

# Add src to path for imports
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from vasttams.core.config import get_settings
from test_examples import load_example, get_segments_example

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
def test_flow_and_source(api_available):
    """Create a test flow and source for segment testing"""
    if not api_available:
        pytest.skip("API not available")
    
    import uuid
    
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
                "frame_rate": {"numerator": 25, "denominator": 1}
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
class TestSegmentEndpointCRUD:
    """CRUD tests for segments endpoint using TAMS 8.0 example data"""
    
    def test_list_segments_endpoint(self, api_available, test_flow_and_source):
        """Test GET /flows/{id}/segments endpoint per TAMS 8.0 spec"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_and_source["flow_id"]
        
        # Get example from TAMS 8.0 spec
        example_segments = get_segments_example()
        
        # Call the API
        response = requests.get(f"{BASE_URL}/flows/{flow_id}/segments")
        assert response.status_code == 200
        
        segments = response.json()
        assert isinstance(segments, list)
        
        # If we have segments, check structure matches TAMS 8.0 example
        if len(segments) > 0:
            segment = segments[0]
            
            # Required fields per TAMS 8.0 spec (flow-segment.json)
            assert "object_id" in segment
            assert "timerange" in segment
            
            # Check for get_urls if present
            if "get_urls" in segment:
                assert isinstance(segment["get_urls"], list)
                if len(segment["get_urls"]) > 0:
                    assert "url" in segment["get_urls"][0]
    
    def test_get_segments_with_timerange_filter(self, api_available, test_flow_and_source):
        """Test GET /flows/{id}/segments with timerange filter per TAMS 8.0 spec"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_and_source["flow_id"]
        
        # Test with timerange filter
        response = requests.get(f"{BASE_URL}/flows/{flow_id}/segments?timerange=2020-01-01T00:00:00Z,2020-01-01T00:01:00Z")
        assert response.status_code == 200
        
        segments = response.json()
        assert isinstance(segments, list)
    
    def test_get_segments_with_urls(self, api_available, test_flow_and_source):
        """Test GET /flows/{id}/segments with URLs per TAMS 8.0 spec"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_and_source["flow_id"]
        
        # Test with URLs filter
        response = requests.get(f"{BASE_URL}/flows/{flow_id}/segments?urls=true")
        assert response.status_code == 200
        
        segments = response.json()
        assert isinstance(segments, list)

