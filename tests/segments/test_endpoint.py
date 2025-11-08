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

from vasttamsserver.core.config import get_settings
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
def test_flow_and_source(api_available, auth_headers):
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
        response = requests.post(f"{BASE_URL}/sources", json=source_data, headers=auth_headers)
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
        
        response = requests.post(f"{BASE_URL}/flows", json=flow_data, headers=auth_headers)
        if response.status_code != 201:
            pytest.skip(f"Failed to create test flow: {response.text}")
        
        yield {"flow_id": flow_id, "source_id": source_id}
        
    finally:
        # Cleanup
        requests.delete(f"{BASE_URL}/flows/{flow_id}", headers=auth_headers)
        requests.delete(f"{BASE_URL}/sources/{source_id}", headers=auth_headers)


@pytest.mark.usefixtures("api_available")
class TestSegmentEndpointCRUD:
    """CRUD tests for segments endpoint using TAMS 8.0 example data"""
    
    def test_list_segments_endpoint(self, api_available, test_flow_and_source, auth_headers):
        """Test GET /flows/{id}/segments endpoint per TAMS 8.0 spec"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_and_source["flow_id"]
        
        # Get example from TAMS 8.0 spec
        example_segments = get_segments_example()
        
        # Call the API
        response = requests.get(f"{BASE_URL}/flows/{flow_id}/segments", headers=auth_headers)
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
    
    def test_get_segments_with_timerange_filter(self, api_available, test_flow_and_source, auth_headers):
        """Test GET /flows/{id}/segments with timerange filter per TAMS 8.0 spec"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_and_source["flow_id"]
        
        # Test with timerange filter
        response = requests.get(f"{BASE_URL}/flows/{flow_id}/segments?timerange=2020-01-01T00:00:00Z,2020-01-01T00:01:00Z", headers=auth_headers)
        assert response.status_code == 200
        
        segments = response.json()
        assert isinstance(segments, list)
    
    def test_get_segments_with_urls(self, api_available, test_flow_and_source, auth_headers):
        """Test GET /flows/{id}/segments with URLs per TAMS 8.0 spec"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_and_source["flow_id"]
        
        # Test with URLs filter
        response = requests.get(f"{BASE_URL}/flows/{flow_id}/segments?urls=true", headers=auth_headers)
        assert response.status_code == 200
        
        segments = response.json()
        assert isinstance(segments, list)
    
    def test_storage_allocation_with_content_type(self, api_available, test_flow_and_source, auth_headers):
        """Test storage allocation includes content-type in put_url per TAMS 8.0 AppNote 0018"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_and_source["flow_id"]
        
        # Request storage allocation
        storage_request = {
            "limit": 1
        }
        
        response = requests.post(
            f"{BASE_URL}/flows/{flow_id}/storage",
            json=storage_request,
            headers=auth_headers
        )
        
        assert response.status_code in [200, 201], f"Failed to allocate storage: {response.text}"
        storage = response.json()
        
        # Verify response structure
        assert "media_objects" in storage
        assert len(storage["media_objects"]) > 0
        
        media_obj = storage["media_objects"][0]
        assert "object_id" in media_obj
        assert "put_url" in media_obj
        
        put_url_obj = media_obj["put_url"]
        assert "url" in put_url_obj
        
        # TAMS 8.0 AppNote 0018 requires content-type in put_url
        assert "content-type" in put_url_obj, "put_url must include content-type per TAMS 8.0 spec"
        
        content_type = put_url_obj["content-type"]
        assert isinstance(content_type, str)
        assert "/" in content_type, "content-type must be a valid MIME type"
        
        # For video flows, should default to video/mp2t
        # (content-type is derived from Flow format/codec)
        logger.info(f"✅ Storage allocation returned content-type: {content_type}")
    
    def test_segments_include_get_urls(self, api_available, test_flow_and_source, auth_headers):
        """Test that segments include get_urls when available per TAMS 8.0 spec"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_and_source["flow_id"]
        
        # Get segments
        response = requests.get(f"{BASE_URL}/flows/{flow_id}/segments", headers=auth_headers)
        assert response.status_code == 200
        
        segments = response.json()
        assert isinstance(segments, list)
        
        # If segments exist, verify get_urls structure when present
        for segment in segments:
            if "get_urls" in segment and segment["get_urls"] is not None:
                get_urls = segment["get_urls"]
                assert isinstance(get_urls, list), "get_urls must be a list"
                
                for get_url in get_urls:
                    assert "url" in get_url, "Each get_url must have a url"
                    assert "storage_id" in get_url, "Each get_url must have storage_id"
                    
                    # Optional fields per TAMS 8.0 spec
                    if "presigned" in get_url:
                        assert isinstance(get_url["presigned"], bool)
                    if "controlled" in get_url:
                        assert isinstance(get_url["controlled"], bool)
                    
                    logger.info(f"✅ Segment has valid get_url: {get_url.get('url', '')[:50]}...")

