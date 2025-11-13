#!/usr/bin/env python3
"""
CRUD Tests for Flows Endpoint

Tests Create, Read, Update, Delete operations for flows per TAMS 8.0 spec.
"""

import pytest
import sys
import requests
from pathlib import Path
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
def clean_flow_id():
    """Generate a clean flow ID for each test"""
    return str(uuid.uuid4())


@pytest.fixture
def test_source_id(auth_headers):
    """Create a test source for flow testing"""
    source_id = str(uuid.uuid4())
    source_data = {
        "id": source_id,
        "format": "urn:x-nmos:format:video",
        "label": f"Test Source {source_id[:8]}"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/sources", json=source_data, headers=auth_headers)
        if response.status_code == 201:
            yield source_id
        else:
            pytest.skip(f"Failed to create test source: {response.text}")
    finally:
        # Cleanup
        requests.delete(f"{BASE_URL}/sources/{source_id}", headers=auth_headers)


@pytest.mark.usefixtures("api_available")
class TestFlowCRUD:
    """Complete CRUD tests for Flows endpoint per TAMS 8.0 spec"""
    
    def test_create_flow(self, clean_flow_id, api_available, test_source_id, auth_headers):
        """Test CREATE operation - POST /flows per TAMS 8.0 spec"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_data = {
            "id": clean_flow_id,
            "source_id": test_source_id,
            "format": "urn:x-nmos:format:video",
            "codec": "video/H264",
            "label": f"CRUD Flow {clean_flow_id[:8]}",
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
        assert response.status_code == 201, f"Failed to create flow: {response.text}"
        
        created = response.json()
        assert created["id"] == clean_flow_id
        assert created["source_id"] == test_source_id
        
        # Cleanup
        requests.delete(f"{BASE_URL}/flows/{clean_flow_id}", headers=auth_headers)
    
    def test_read_flow(self, clean_flow_id, api_available, test_source_id, auth_headers):
        """Test READ operation - GET /flows/{id} per TAMS 8.0 spec"""
        if not api_available:
            pytest.skip("API not available")
        
        # Create a flow first
        flow_data = {
            "id": clean_flow_id,
            "source_id": test_source_id,
            "format": "urn:x-nmos:format:video",
            "codec": "video/H264",
            "label": f"Read Flow {clean_flow_id[:8]}",
            "essence_parameters": {
                "frame_width": 1920,
                "frame_height": 1080,
                "frame_rate": {"numerator": 25, "denominator": 1}
            }
        }
        requests.post(f"{BASE_URL}/flows", json=flow_data, headers=auth_headers)
        
        # Read it back
        response = requests.get(f"{BASE_URL}/flows/{clean_flow_id}", headers=auth_headers)
        assert response.status_code == 200
        
        retrieved = response.json()
        assert retrieved["id"] == clean_flow_id
        assert retrieved["source_id"] == test_source_id
        
        # Cleanup
        requests.delete(f"{BASE_URL}/flows/{clean_flow_id}", headers=auth_headers)
    
    def test_list_flows(self, api_available, auth_headers):
        """Test READ operation - GET /flows (list) per TAMS 8.0 spec"""
        if not api_available:
            pytest.skip("API not available")
        
        response = requests.get(f"{BASE_URL}/flows", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "data" in data
        assert isinstance(data["data"], list)
        
        # Verify each flow has required fields
        for flow in data["data"]:
            assert "id" in flow
            assert "source_id" in flow
            assert "format" in flow
    
    def test_delete_flow(self, clean_flow_id, api_available, test_source_id, auth_headers):
        """Test DELETE operation - DELETE /flows/{id} per TAMS 8.0 spec"""
        if not api_available:
            pytest.skip("API not available")
        
        # Create a flow first
        flow_data = {
            "id": clean_flow_id,
            "source_id": test_source_id,
            "format": "urn:x-nmos:format:video",
            "codec": "video/H264",
            "label": f"Delete Flow {clean_flow_id[:8]}",
            "essence_parameters": {
                "frame_width": 1920,
                "frame_height": 1080,
                "frame_rate": {"numerator": 25, "denominator": 1}
            }
        }
        requests.post(f"{BASE_URL}/flows", json=flow_data, headers=auth_headers)
        
        # Delete it
        response = requests.delete(f"{BASE_URL}/flows/{clean_flow_id}", headers=auth_headers)
        assert response.status_code in [200, 204], f"Failed to delete flow: {response.text}"
        
        # Verify deletion
        response = requests.get(f"{BASE_URL}/flows/{clean_flow_id}", headers=auth_headers)
        assert response.status_code == 404

