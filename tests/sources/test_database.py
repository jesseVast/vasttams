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
def clean_source_id():
    """Generate a clean source ID for each test"""
    return str(uuid.uuid4())


@pytest.mark.usefixtures("api_available")
class TestSourceDatabaseIntegration:
    """Integration tests for Sources against real database"""
    
    def test_create_source_in_database(self, clean_source_id, api_available):
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
        
        response = requests.post(f"{BASE_URL}/sources", json=source_data)
        assert response.status_code == 201, f"Failed to create source: {response.text}"
        created = response.json()
        
        assert created["id"] == clean_source_id
        assert created["format"] == "urn:x-nmos:format:video"
        assert created["label"] == source_data["label"]
        
        # Verify we can retrieve it
        response = requests.get(f"{BASE_URL}/sources/{clean_source_id}")
        assert response.status_code == 200
        retrieved = response.json()
        assert retrieved["id"] == clean_source_id
        
        # Cleanup - delete the source
        response = requests.delete(f"{BASE_URL}/sources/{clean_source_id}")
        assert response.status_code in [200, 204], f"Failed to cleanup source: {response.text}"
    
    def test_list_sources_from_database(self, api_available):
        """Test listing sources from the database"""
        if not api_available:
            pytest.skip("API not available")
        
        response = requests.get(f"{BASE_URL}/sources")
        assert response.status_code == 200
        
        data = response.json()
        assert "data" in data
        assert isinstance(data["data"], list)
    
    def test_create_and_get_source_with_tags(self, clean_source_id, api_available):
        """Test creating a source with tags and retrieving them"""
        if not api_available:
            pytest.skip("API not available")
        
        # Create source
        source_data = {
            "id": clean_source_id,
            "format": "urn:x-nmos:format:video",
            "label": f"Tagged Source {clean_source_id[:8]}"
        }
        response = requests.post(f"{BASE_URL}/sources", json=source_data)
        assert response.status_code == 201
        
        # Add a tag
        tag_value = "test-environment"
        response = requests.put(
            f"{BASE_URL}/sources/{clean_source_id}/tags/environment",
            data=tag_value,
            headers={"Content-Type": "text/plain"}
        )
        # Accept 200, 201, or 204 for tag creation
        assert response.status_code in [200, 201, 204], f"Failed to add tag: {response.text}"
        
        # Retrieve tags
        response = requests.get(f"{BASE_URL}/sources/{clean_source_id}/tags")
        if response.status_code == 200:
            tags = response.json()
            assert "environment" in tags
            assert tags["environment"] == "test-environment"
        
        # Cleanup
        requests.delete(f"{BASE_URL}/sources/{clean_source_id}")
    
    def test_filter_sources_by_format(self, api_available):
        """Test filtering sources by format"""
        if not api_available:
            pytest.skip("API not available")
        
        # Test with format filter
        response = requests.get(f"{BASE_URL}/sources?format=urn:x-nmos:format:video")
        assert response.status_code == 200
        
        data = response.json()
        assert "data" in data
        
        # Verify all returned sources match the format
        for source in data["data"]:
            assert source["format"] == "urn:x-nmos:format:video"


@pytest.mark.usefixtures("api_available")
class TestSourceBatchOperations:
    """Test batch source operations against database"""
    
    def test_create_batch_sources(self, api_available):
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
        
        response = requests.post(f"{BASE_URL}/sources/batch", json=batch_data)
        assert response.status_code == 201
        created = response.json()
        
        assert isinstance(created, list)
        assert len(created) == 2
        
        # Cleanup
        for source_id in source_ids:
            requests.delete(f"{BASE_URL}/sources/{source_id}")

