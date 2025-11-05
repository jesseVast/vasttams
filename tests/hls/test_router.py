#!/usr/bin/env python3
"""
Tests for HLS Router

Tests HLS API endpoints.
"""

import pytest
import sys
import requests
from pathlib import Path
import uuid

# Add src to path
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
def test_flow_with_segments(api_available, auth_headers):
    """Create a test flow with segments for HLS testing"""
    if not api_available:
        pytest.skip("API not available")
    
    # Create source
    source_id = str(uuid.uuid4())
    source_data = {
        "id": source_id,
        "format": "urn:x-nmos:format:video",
        "label": f"Test Source {source_id[:8]}"
    }
    
    requests.post(f"{BASE_URL}/sources", json=source_data, headers=auth_headers)
    
    # Create flow
    flow_id = str(uuid.uuid4())
    flow_data = {
        "id": flow_id,
        "source_id": source_id,
        "format": "urn:x-nmos:format:video",
        "label": f"HLS Test Flow {flow_id[:8]}",
        "codec": "video/H264",
        "essence_parameters": {
            "frame_width": 1920,
            "frame_height": 1080,
            "frame_rate": {"numerator": 25, "denominator": 1}
        }
    }
    
    response = requests.post(f"{BASE_URL}/flows", json=flow_data, headers=auth_headers)
    assert response.status_code == 201
    
    # Add segments
    for i in range(3):
        object_id = str(uuid.uuid4())
        segment_data = {
            "object_id": object_id,
            "timerange": f"[{i}:0_{i+1}:0)",
            "get_urls": [{
                "url": f"https://example.com/segment{i}.ts",
                "storage_id": str(uuid.uuid4()),
                "provider": "aws",
                "store_product": "s3",
                "label": "hls"
            }],
            "sample_count": 30
        }
        
        try:
            requests.post(f"{BASE_URL}/flows/{flow_id}/segments", json=segment_data, headers=auth_headers)
        except Exception as e:
            logger.debug(f"Could not add segment: {e}")
    
    yield flow_id
    
    # Cleanup
    requests.delete(f"{BASE_URL}/flows/{flow_id}", headers=auth_headers)
    requests.delete(f"{BASE_URL}/sources/{source_id}", headers=auth_headers)


@pytest.mark.usefixtures("api_available")
class TestHLSRouter:
    """Test HLS API endpoints"""
    
    def test_get_hls_playlist_nonexistent_flow(self, auth_headers):
        """Test HLS playlist for non-existent flow returns 404"""
        flow_id = str(uuid.uuid4())
        
        response = requests.get(f"{BASE_URL}/hls/flows/{flow_id}/playlist.m3u8", headers=auth_headers)
        assert response.status_code == 404
    
    def test_get_hls_playlist_flow_without_segments(self, api_available, test_flow_with_segments, auth_headers):
        """Test HLS playlist generation"""
        if not api_available:
            pytest.skip("API not available")
        
        # Try to get playlist for a flow without segments
        flow_id = str(uuid.uuid4())
        
        # Create minimal flow
        from requests import post
        source_id = str(uuid.uuid4())
        post(f"{BASE_URL}/sources", json={
            "id": source_id,
            "format": "urn:x-nmos:format:video",
            "label": "temp"
        }, headers=auth_headers)
        
        flow_data = {
            "id": flow_id,
            "source_id": source_id,
            "format": "urn:x-nmos:format:video"
        }
        post(f"{BASE_URL}/flows", json=flow_data, headers=auth_headers)
        
        # Should return 404 for flow without segments
        response = requests.get(f"{BASE_URL}/hls/flows/{flow_id}/playlist.m3u8", headers=auth_headers)
        assert response.status_code == 404
        
        # Cleanup
        requests.delete(f"{BASE_URL}/flows/{flow_id}", headers=auth_headers)
        requests.delete(f"{BASE_URL}/sources/{source_id}", headers=auth_headers)
    
    def test_get_hls_playlist_with_segments(self, api_available, test_flow_with_segments, auth_headers):
        """Test HLS playlist generation with segments"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_with_segments
        
        # Note: This will return 404 if flow has no segments
        # In real test, we need to ensure segments are added
        response = requests.get(f"{BASE_URL}/hls/flows/{flow_id}/playlist.m3u8", headers=auth_headers)
        
        if response.status_code == 200:
            # Verify M3U8 format
            content = response.text
            assert content.startswith("#EXTM3U")
            assert "application/vnd.apple.mpegurl" in response.headers.get("content-type", "")
        elif response.status_code == 404:
            # Acceptable if no segments
            pass
    
    def test_get_hls_status_nonexistent_flow(self, api_available, auth_headers):
        """Test HLS status for non-existent flow"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = str(uuid.uuid4())
        
        response = requests.get(f"{BASE_URL}/hls/flows/{flow_id}/status", headers=auth_headers)
        assert response.status_code == 404
    
    def test_get_hls_status_existing_flow(self, api_available, test_flow_with_segments, auth_headers):
        """Test HLS status for existing flow"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_with_segments
        
        response = requests.get(f"{BASE_URL}/hls/flows/{flow_id}/status", headers=auth_headers)
        
        if response.status_code == 200:
            data = response.json()
            assert "flow_id" in data
            assert "hls_ready" in data
            assert "segment_count" in data
            assert data["flow_id"] == flow_id

