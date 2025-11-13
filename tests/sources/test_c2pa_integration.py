#!/usr/bin/env python3
"""
C2PA Integration Tests for Sources

Tests C2PA validation during source creation.
"""

import pytest
import sys
import requests
import json
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


@pytest.mark.usefixtures("api_available")
class TestC2PAInSourceCreation:
    """Test C2PA validation during source creation"""
    
    def test_create_source_with_valid_c2pa_tags(self, api_available, auth_headers):
        """Test creating a source with valid C2PA tags"""
        if not api_available:
            pytest.skip("API not available")
        
        source_id = str(uuid.uuid4())
        
        source_data = {
            "id": source_id,
            "format": "urn:x-nmos:format:video",
            "label": f"Test Source {source_id[:8]}",
            "tags": {
                "c2pa": json.dumps({
                    "version": "1.0",
                    "assertions": [
                        {
                            "assertion_type": "claim",
                            "assertion_data": {
                                "source": "camera_01",
                                "timestamp": "2024-01-01T00:00:00Z"
                            }
                        }
                    ],
                    "metadata": {
                        "creator": "BBC TAMS"
                    }
                })
            }
        }
        
        response = requests.post(f"{BASE_URL}/sources", json=source_data, headers=auth_headers)
        # Should succeed (C2PA validation logs warning but doesn't reject)
        assert response.status_code == 201, f"Failed to create source with C2PA: {response.text}"
        
        # Verify source was created
        response = requests.get(f"{BASE_URL}/sources/{source_id}", headers=auth_headers)
        assert response.status_code == 200
        source = response.json()
        assert source["id"] == source_id
        
        # Cleanup
        requests.delete(f"{BASE_URL}/sources/{source_id}", headers=auth_headers)
    
    def test_create_source_with_invalid_c2pa_tags(self, api_available, auth_headers):
        """Test creating a source with invalid C2PA tags"""
        if not api_available:
            pytest.skip("API not available")
        
        source_id = str(uuid.uuid4())
        
        source_data = {
            "id": source_id,
            "format": "urn:x-nmos:format:video",
            "label": f"Test Source {source_id[:8]}",
            "tags": {
                "c2pa": "invalid_string"  # Invalid C2PA structure
            }
        }
        
        response = requests.post(f"{BASE_URL}/sources", json=source_data, headers=auth_headers)
        # Should still succeed (C2PA validation warns but doesn't reject)
        assert response.status_code == 201, f"Failed to create source with invalid C2PA: {response.text}"
        
        # Cleanup
        requests.delete(f"{BASE_URL}/sources/{source_id}", headers=auth_headers)
    
    def test_create_source_without_c2pa(self, api_available, auth_headers):
        """Test creating a source without C2PA data"""
        if not api_available:
            pytest.skip("API not available")
        
        source_id = str(uuid.uuid4())
        
        source_data = {
            "id": source_id,
            "format": "urn:x-nmos:format:video",
            "label": f"Test Source {source_id[:8]}"
            # No tags
        }
        
        response = requests.post(f"{BASE_URL}/sources", json=source_data, headers=auth_headers)
        assert response.status_code == 201, f"Failed to create source: {response.text}"
        
        # Verify source was created
        response = requests.get(f"{BASE_URL}/sources/{source_id}", headers=auth_headers)
        assert response.status_code == 200
        
        # Cleanup
        requests.delete(f"{BASE_URL}/sources/{source_id}", headers=auth_headers)

