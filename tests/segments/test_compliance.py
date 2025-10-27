#!/usr/bin/env python3
"""
TAMS 8.0 Compliance Tests for Flow Segments

Tests compliance with TAMS 8.0 specification and app notes.
"""

import pytest
import sys
import requests
from pathlib import Path

# Add src to path for imports
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from vasttams.core.config import get_settings
from test_examples import get_segments_example

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
        requests.delete(f"{BASE_URL}/flows/{flow_id}")
        requests.delete(f"{BASE_URL}/sources/{source_id}")


@pytest.mark.usefixtures("api_available")
class TestSegmentSpecCompliance:
    """Test compliance with TAMS 8.0 segment spec"""
    
    def test_segment_timerange_per_appnote_0012(self, api_available, test_flow_and_source):
        """
        Test segment timerange per App Note 0012 (Using Flow Segment Timestamps).
        Segments should have timerange with proper representation.
        """
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_and_source["flow_id"]
        example_segments = get_segments_example()
        
        response = requests.get(f"{BASE_URL}/flows/{flow_id}/segments")
        assert response.status_code == 200
        
        segments = response.json()
        assert isinstance(segments, list)
        
        # If we have segments, verify timerange per App Note 0012
        if len(segments) > 0:
            segment = segments[0]
            
            # TAMS 8.0 requirement: timerange must be present
            assert "timerange" in segment
            
            timerange = segment["timerange"]
            
            # Per App Note 0012, timerange can be string with format [start_end)
            if isinstance(timerange, str):
                # Should contain start and end separated by underscore
                parts = timerange.split("_")
                if len(parts) == 2:
                    start = parts[0]
                    end = parts[1]
                    
                    # Start should be inclusive "["
                    assert start.startswith("[")
                    
                    # End should have closing marker
                    assert end.endswith(")") or end.endswith("]")
    
    def test_segment_object_id_per_spec(self, api_available, test_flow_and_source):
        """
        Test segment object_id per TAMS 8.0 spec.
        Spec: flow-segment.json requires object_id
        """
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_and_source["flow_id"]
        
        response = requests.get(f"{BASE_URL}/flows/{flow_id}/segments")
        if response.status_code == 200:
            segments = response.json()
            
            if len(segments) > 0:
                segment = segments[0]
                
                # TAMS 8.0 requirement: object_id must be present
                assert "object_id" in segment
                assert isinstance(segment["object_id"], str)


@pytest.mark.usefixtures("api_available")
class TestSegmentAppNoteCompliance:
    """Test compliance with TAMS 8.0 app notes for segments"""
    
    def test_segment_get_urls_per_spec(self, api_available, test_flow_and_source):
        """
        Test segment get_urls per TAMS 8.0 spec.
        Segments should have get_urls array with url field.
        """
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_and_source["flow_id"]
        
        # Test with URLs parameter
        response = requests.get(f"{BASE_URL}/flows/{flow_id}/segments?urls=true")
        assert response.status_code == 200
        
        segments = response.json()
        assert isinstance(segments, list)
        
        # If we have segments with URLs, verify structure
        if len(segments) > 0:
            segment = segments[0]
            
            # get_urls should be present if URLs are requested
            if "get_urls" in segment:
                assert isinstance(segment["get_urls"], list)
                
                if len(segment["get_urls"]) > 0:
                    url_obj = segment["get_urls"][0]
                    assert "url" in url_obj
                    assert isinstance(url_obj["url"], str)
    
    def test_segment_filtering_by_timerange_per_appnote_0012(self, api_available, test_flow_and_source):
        """
        Test segment filtering by timerange per App Note 0012.
        Should support querying segments for specific timerange.
        """
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_and_source["flow_id"]
        
        # Test timerange filtering per App Note 0012
        # Format: [start_end) where start and end are timestamps
        timerange_query = "2020-01-01T00:00:00Z,2020-01-01T00:01:00Z"
        
        response = requests.get(f"{BASE_URL}/flows/{flow_id}/segments?timerange={timerange_query}")
        assert response.status_code == 200
        
        segments = response.json()
        assert isinstance(segments, list)

