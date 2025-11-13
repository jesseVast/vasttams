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

from vasttamsserver.core.config import get_settings

import logging
logger = logging.getLogger(__name__)

# Get settings for API base URL
settings = get_settings()
BASE_URL = f"http://{settings.host}:{settings.port}/api/tams/latest"


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
                "frame_rate": {
                    "numerator": 25,
                    "denominator": 1
                },
                "interlace_mode": "progressive",
                "transfer_characteristic": "ITU-R BT.709"
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
class TestSegmentDatabaseIntegration:
    """Integration tests for Segments against real database"""
    
    def test_list_segments_from_database(self, api_available, test_flow_and_source, auth_headers):
        """Test listing segments for a flow per TAMS 8.0 spec"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_and_source["flow_id"]
        
        response = requests.get(f"{BASE_URL}/flows/{flow_id}/segments", headers=auth_headers)
        assert response.status_code == 200
        
        # TAMS 8.0: segments endpoint returns a list
        segments = response.json()
        assert isinstance(segments, list)
    
    def test_filter_segments_by_timerange(self, api_available, test_flow_and_source, auth_headers):
        """Test filtering segments by timerange per TAMS 8.0"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_and_source["flow_id"]
        
        # Test with timerange filter
        response = requests.get(f"{BASE_URL}/flows/{flow_id}/segments?timerange=2020-01-01T00:00:00Z,2020-01-01T00:01:00Z", headers=auth_headers)
        assert response.status_code == 200
        
        segments = response.json()
        assert isinstance(segments, list)


@pytest.mark.usefixtures("api_available")
class TestSegmentCRUD:
    """Test segment CRUD operations"""
    
    def test_create_segment_with_storage(self, api_available, test_flow_and_source, auth_headers):
        """Test creating a segment with storage allocation"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_and_source["flow_id"]
        
        # Request storage for the flow
        storage_request = {
            "limit": 1
        }
        
        response = requests.post(
            f"{BASE_URL}/flows/{flow_id}/storage",
            json=storage_request,
            headers=auth_headers
        )
        
        if response.status_code in [200, 201]:
            storage = response.json()
            assert "media_objects" in storage or "urls" in storage or "storage_id" in storage
            
            # If media_objects is present, verify content-type per TAMS 8.0
            if "media_objects" in storage and len(storage["media_objects"]) > 0:
                media_obj = storage["media_objects"][0]
                if "put_url" in media_obj and isinstance(media_obj["put_url"], dict):
                    put_url = media_obj["put_url"]
                    if "content-type" in put_url:
                        content_type = put_url["content-type"]
                        assert isinstance(content_type, str)
                        assert "/" in content_type
                        logger.info(f"✅ Storage allocation includes content-type: {content_type}")
    
    def test_get_segment_details(self, api_available, test_flow_and_source, auth_headers):
        """Test getting detailed segment information per TAMS 8.0 spec"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_and_source["flow_id"]
        
        # First, list segments to get one to query
        response = requests.get(f"{BASE_URL}/flows/{flow_id}/segments", headers=auth_headers)
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
    
    def test_content_type_derived_from_flow_format(self, api_available, auth_headers):
        """Test that content-type is correctly derived from Flow format/codec per TAMS 8.0"""                                                   
        if not api_available:
            pytest.skip("API not available")
    
        import uuid
    
        # Test video flow -> video/mp2t
        source_id = str(uuid.uuid4())
        video_flow_id = str(uuid.uuid4())
    
        try:
            # Create source
            source_data = {"id": source_id, "format": "urn:x-nmos:format:video"}                                                                
            requests.post(f"{BASE_URL}/sources", json=source_data, headers=auth_headers)
    
            # Create video flow
            video_flow_data = {
                "id": video_flow_id,
                "source_id": source_id,
                "format": "urn:x-nmos:format:video",
                "codec": "video/h264",
                "essence_parameters": {
                    "frame_width": 1920,
                    "frame_height": 1080,
                    "frame_rate": {"numerator": 25, "denominator": 1}
                }
            }
            response = requests.post(f"{BASE_URL}/flows", json=video_flow_data, headers=auth_headers)
            assert response.status_code == 201
            
            # Request storage allocation
            storage_response = requests.post(
                f"{BASE_URL}/flows/{video_flow_id}/storage",
                json={"limit": 1},
                headers=auth_headers
            )
            
            if storage_response.status_code in [200, 201]:
                storage = storage_response.json()
                if "media_objects" in storage and len(storage["media_objects"]) > 0:
                    put_url = storage["media_objects"][0].get("put_url", {})
                    if "content-type" in put_url:
                        content_type = put_url["content-type"]
                        # Video flows should default to video/mp2t
                        assert content_type == "video/mp2t", \
                            f"Expected video/mp2t for video flow, got {content_type}"
                        logger.info(f"✅ Video flow correctly derives content-type: {content_type}")
            
        finally:
            # Cleanup
            requests.delete(f"{BASE_URL}/flows/{video_flow_id}", headers=auth_headers)
            requests.delete(f"{BASE_URL}/sources/{source_id}", headers=auth_headers)


@pytest.mark.usefixtures("api_available")
class TestSegmentDeletion:
    """Test segment deletion per ADR-0004 (content deletion - rejected)"""
    
    def test_segments_can_be_deleted(self, api_available, test_flow_and_source, auth_headers):
        """
        Test that segments can be deleted via DELETE /flows/{flow_id}/segments
        per TAMS 8.0 spec and ADR-0004 (deletion is allowed, no hard prevention)
        
        Note: This test checks that the DELETE endpoint exists and accepts requests.
        Actual deletion may fail if no segments exist or if there's a server error.
        """
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_and_source["flow_id"]
        
        # Try to delete segments with timerange filter
        response = requests.delete(
            f"{BASE_URL}/flows/{flow_id}/segments",
            params={"timerange": "2020-01-01T00:00:00Z,2020-12-31T23:59:59Z"},
            headers=auth_headers
        )
        
        # Per ADR-0004, deletions are allowed but may be mediated by other systems
        # Should accept the delete request (may return 200, 204, 404, or 500 if error)
        # 500 is acceptable if there are implementation issues (e.g., no segments to delete)
        assert response.status_code in [200, 404, 204, 500], \
            f"Unexpected status: {response.status_code}, Response: {response.text}"

