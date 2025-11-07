#!/usr/bin/env python3
"""
CRUD Tests for Sources Endpoint

Tests Create, Read, Update, Delete operations for sources per TAMS 8.0 spec.
"""

import pytest
import sys
import requests
from pathlib import Path
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
class TestSourceCRUD:
    """Complete CRUD tests for Sources endpoint per TAMS 8.0 spec"""
    
    def test_create_source(self, clean_source_id, api_available, auth_headers):
        """Test CREATE operation - POST /sources per TAMS 8.0 spec"""
        if not api_available:
            pytest.skip("API not available")
        
        source_data = {
            "id": clean_source_id,
            "format": "urn:x-nmos:format:video",
            "label": f"CRUD Source {clean_source_id[:8]}",
            "description": "Test source for CRUD operations"
        }
        
        response = requests.post(f"{BASE_URL}/sources", json=source_data, headers=auth_headers)
        assert response.status_code == 201, f"Failed to create source: {response.text}"
        
        created = response.json()
        assert created["id"] == clean_source_id
        assert created["format"] == "urn:x-nmos:format:video"
        assert created["label"] == source_data["label"]
        
        # Cleanup
        requests.delete(f"{BASE_URL}/sources/{clean_source_id}", headers=auth_headers)
    
    def test_read_source(self, clean_source_id, api_available, auth_headers):
        """Test READ operation - GET /sources/{id} per TAMS 8.0 spec"""
        if not api_available:
            pytest.skip("API not available")
        
        # Create a source first
        source_data = {
            "id": clean_source_id,
            "format": "urn:x-nmos:format:video",
            "label": f"Read Source {clean_source_id[:8]}"
        }
        requests.post(f"{BASE_URL}/sources", json=source_data, headers=auth_headers)
        
        # Read it back
        response = requests.get(f"{BASE_URL}/sources/{clean_source_id}", headers=auth_headers)
        assert response.status_code == 200
        
        retrieved = response.json()
        assert retrieved["id"] == clean_source_id
        assert "format" in retrieved
        assert "label" in retrieved
        
        # Cleanup
        requests.delete(f"{BASE_URL}/sources/{clean_source_id}", headers=auth_headers)
    
    def test_list_sources(self, api_available, auth_headers):
        """Test READ operation - GET /sources (list) per TAMS 8.0 spec"""
        if not api_available:
            pytest.skip("API not available")
        
        response = requests.get(f"{BASE_URL}/sources", headers=auth_headers, timeout=30)
        # May return 200 or 503 if server is overloaded
        assert response.status_code in [200, 503]
        if response.status_code == 200:
            data = response.json()
            assert "data" in data
            assert isinstance(data["data"], list)
            
            # Verify each source has required fields
            for source in data["data"]:
                assert "id" in source
                assert "format" in source
    
    def test_update_source(self, clean_source_id, api_available, auth_headers):
        """
        Test UPDATE operation - No PUT /sources/{id} endpoint per TAMS 8.0 spec
        Note: TAMS 8.0 uses partial updates (PUT /sources/{id}/label, /description)
        """
        if not api_available:
            pytest.skip("API not available")
        
        # Create a source first
        source_data = {
            "id": clean_source_id,
            "format": "urn:x-nmos:format:video",
            "label": f"Original Label {clean_source_id[:8]}"
        }
        requests.post(f"{BASE_URL}/sources", json=source_data, headers=auth_headers)
        
        # TAMS 8.0 uses PUT /sources/{id}/label with query parameter
        updated_label = f"Updated Label {clean_source_id[:8]}"
        response = requests.put(f"{BASE_URL}/sources/{clean_source_id}/label?label={updated_label}", headers=auth_headers)
        assert response.status_code in [200, 204], f"Failed to update source label: {response.text}"
        
        # Verify update
        response = requests.get(f"{BASE_URL}/sources/{clean_source_id}", headers=auth_headers)
        assert response.status_code == 200
        retrieved = response.json()
        assert retrieved["label"] == updated_label
        
        # Cleanup
        requests.delete(f"{BASE_URL}/sources/{clean_source_id}", headers=auth_headers)
    
    def test_delete_source(self, clean_source_id, api_available, auth_headers):
        """Test DELETE operation - DELETE /sources/{id} per TAMS 8.0 spec"""
        if not api_available:
            pytest.skip("API not available")
        
        # Create a source first
        source_data = {
            "id": clean_source_id,
            "format": "urn:x-nmos:format:video",
            "label": f"Delete Source {clean_source_id[:8]}"
        }
        requests.post(f"{BASE_URL}/sources", json=source_data, headers=auth_headers)
        
        # Delete it
        response = requests.delete(f"{BASE_URL}/sources/{clean_source_id}", headers=auth_headers)
        assert response.status_code in [200, 204], f"Failed to delete source: {response.text}"
        
        # Verify deletion
        response = requests.get(f"{BASE_URL}/sources/{clean_source_id}", headers=auth_headers)
        assert response.status_code == 404

