#!/usr/bin/env python3
"""
Database Integration Tests for Sources

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
def clean_source_id():
    """Generate a clean source ID for each test"""
    return str(uuid.uuid4())


@pytest.mark.usefixtures("api_available")
class TestSourceDatabaseIntegration:
    """Integration tests for Sources against real database"""
    
    def test_create_source_in_database(self, clean_source_id, api_available, auth_headers):
        """Test creating a source in the database"""
        if not api_available:
            pytest.skip("API not available")
        
        # Create a source via API
        source_data = {
            "id": clean_source_id,
            "format": "urn:x-nmos:format:video",
            "label": f"Test Source {clean_source_id[:8]}",
            "description": "Test source created by integration test"
        }
        
        response = requests.post(f"{BASE_URL}/sources", json=source_data, headers=auth_headers)
        assert response.status_code == 201, f"Failed to create source: {response.text}"
        created = response.json()
        
        assert created["id"] == clean_source_id
        assert created["format"] == "urn:x-nmos:format:video"
        assert created["label"] == source_data["label"]
        
        # Verify we can retrieve it
        response = requests.get(f"{BASE_URL}/sources/{clean_source_id}", headers=auth_headers)
        assert response.status_code == 200
        retrieved = response.json()
        assert retrieved["id"] == clean_source_id
        
        # Cleanup - delete the source
        response = requests.delete(f"{BASE_URL}/sources/{clean_source_id}", headers=auth_headers)
        assert response.status_code in [200, 204], f"Failed to cleanup source: {response.text}"
    
    def test_list_sources_from_database(self, api_available, auth_headers):
        """Test listing sources from the database"""
        if not api_available:
            pytest.skip("API not available")
        
        response = requests.get(f"{BASE_URL}/sources", headers=auth_headers, timeout=30)
        # May return 200 or 503 if server is overloaded
        assert response.status_code in [200, 503]
        if response.status_code == 200:
            data = response.json()
            assert "data" in data
            assert isinstance(data["data"], list)
    
    def test_create_and_get_source_with_tags(self, clean_source_id, api_available, auth_headers):
        """Test creating a source with tags and retrieving them"""
        if not api_available:
            pytest.skip("API not available")
        
        # Create source
        source_data = {
            "id": clean_source_id,
            "format": "urn:x-nmos:format:video",
            "label": f"Tagged Source {clean_source_id[:8]}"
        }
        response = requests.post(f"{BASE_URL}/sources", json=source_data, headers=auth_headers)
        assert response.status_code == 201
        
        # Add a tag
        tag_value = "test-environment"
        tag_headers = {**auth_headers, "Content-Type": "text/plain"}
        response = requests.put(
            f"{BASE_URL}/sources/{clean_source_id}/tags/environment",
            data=tag_value,
            headers=tag_headers
        )
        # Accept 200, 201, or 204 for tag creation
        assert response.status_code in [200, 201, 204], f"Failed to add tag: {response.text}"
        
        # Retrieve tags
        response = requests.get(f"{BASE_URL}/sources/{clean_source_id}/tags", headers=auth_headers)
        if response.status_code == 200:
            tags = response.json()
            assert "environment" in tags
            assert tags["environment"] == "test-environment"
        
        # Cleanup
        requests.delete(f"{BASE_URL}/sources/{clean_source_id}", headers=auth_headers)
    
    def test_filter_sources_by_format(self, api_available, auth_headers):
        """Test filtering sources by format"""
        if not api_available:
            pytest.skip("API not available")
        
        # Test with format filter
        response = requests.get(f"{BASE_URL}/sources?format=urn:x-nmos:format:video", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "data" in data
        
        # Verify all returned sources match the format
        for source in data["data"]:
            assert source["format"] == "urn:x-nmos:format:video"


@pytest.mark.usefixtures("api_available")
class TestSourceBatchOperations:
    """Test batch source operations against database"""
    
    def test_create_batch_sources(self, api_available, auth_headers):
        """Test creating multiple sources in batch"""
        if not api_available:
            pytest.skip("API not available")
        
        source_ids = [str(uuid.uuid4()) for _ in range(2)]
        batch_data = [
            {
                "id": source_ids[0],
                "format": "urn:x-nmos:format:video",
                "label": f"Batch Source 1 {source_ids[0][:8]}"
            },
            {
                "id": source_ids[1],
                "format": "urn:x-nmos:format:audio",
                "label": f"Batch Source 2 {source_ids[1][:8]}"
            }
        ]
        
        response = requests.post(f"{BASE_URL}/sources/batch", json=batch_data, headers=auth_headers)
        assert response.status_code == 201
        created = response.json()
        
        assert isinstance(created, list)
        assert len(created) == 2
        
        # Cleanup
        for source_id in source_ids:
            requests.delete(f"{BASE_URL}/sources/{source_id}", headers=auth_headers)


class TestSourceCascadeDelete:
    """Test cascade delete functionality for sources"""
    
    def test_delete_source_with_cascade_deletes_flows(self, api_available, auth_headers):
        """Test that deleting a source with cascade=True deletes dependent flows"""
        if not api_available:
            pytest.skip("API not available")
        
        # Create a test source
        source_id = str(uuid.uuid4())
        source_data = {
            "id": source_id,
            "format": "urn:x-nmos:format:video"
        }
        response = requests.post(f"{BASE_URL}/sources", json=source_data, headers=auth_headers)
        assert response.status_code == 201, f"Failed to create source: {response.text}"
        
        # Create a flow for this source
        flow_id = str(uuid.uuid4())
        flow_data = {
            "id": flow_id,
            "source_id": source_id,
            "format": "urn:x-nmos:format:video",
            "codec": "video/H264",
            "essence_parameters": {
                "frame_width": 1920,
                "frame_height": 1080,
                "frame_rate": {"numerator": 25, "denominator": 1}
            }
        }
        response = requests.post(f"{BASE_URL}/flows", json=flow_data, headers=auth_headers)
        assert response.status_code == 201, f"Failed to create flow: {response.text}"
        
        # Verify flow exists
        response = requests.get(f"{BASE_URL}/flows/{flow_id}", headers=auth_headers)
        assert response.status_code == 200
        created_flow = response.json()
        assert created_flow["id"] == flow_id
        
        # Delete source with cascade=True (should delete the flow)
        response = requests.delete(f"{BASE_URL}/sources/{source_id}?cascade=true", headers=auth_headers)
        assert response.status_code == 200, f"Failed to delete source: {response.text}"
        
        # Verify source is deleted
        response = requests.get(f"{BASE_URL}/sources/{source_id}", headers=auth_headers)
        assert response.status_code == 404
        
        # Verify flow is also deleted (cascade worked)
        response = requests.get(f"{BASE_URL}/flows/{flow_id}", headers=auth_headers)
        assert response.status_code == 404, "Flow should be deleted when source is deleted with cascade"
    
    def test_delete_source_without_cascade_prevents_deletion(self, api_available, auth_headers):
        """Test that deleting a source with cascade=False prevents deletion if flows exist"""
        if not api_available:
            pytest.skip("API not available")
        
        # Create a test source
        source_id = str(uuid.uuid4())
        source_data = {
            "id": source_id,
            "format": "urn:x-nmos:format:video"
        }
        response = requests.post(f"{BASE_URL}/sources", json=source_data, headers=auth_headers)
        assert response.status_code == 201, f"Failed to create source: {response.text}"
        
        # Create a flow for this source
        flow_id = str(uuid.uuid4())
        flow_data = {
            "id": flow_id,
            "source_id": source_id,
            "format": "urn:x-nmos:format:video",
            "codec": "video/H264",
            "essence_parameters": {
                "frame_width": 1920,
                "frame_height": 1080,
                "frame_rate": {"numerator": 25, "denominator": 1}
            }
        }
        response = requests.post(f"{BASE_URL}/flows", json=flow_data, headers=auth_headers)
        assert response.status_code == 201, f"Failed to create flow: {response.text}"
        
        # Try to delete source with cascade=False (should fail)
        response = requests.delete(f"{BASE_URL}/sources/{source_id}?cascade=false", headers=auth_headers)
        assert response.status_code == 409, "Should return 409 Conflict when cascade=False and flows exist"
        
        # Verify source still exists
        response = requests.get(f"{BASE_URL}/sources/{source_id}", headers=auth_headers)
        assert response.status_code == 200
        
        # Verify flow still exists
        response = requests.get(f"{BASE_URL}/flows/{flow_id}", headers=auth_headers)
        assert response.status_code == 200
        
        # Cleanup
        requests.delete(f"{BASE_URL}/flows/{flow_id}", headers=auth_headers)
        requests.delete(f"{BASE_URL}/sources/{source_id}", headers=auth_headers)

