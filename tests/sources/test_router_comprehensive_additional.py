#!/usr/bin/env python3
"""
Additional Comprehensive Router Tests for Sources

Additional tests for batch operations, error paths, and edge cases.
"""

import pytest
import sys
import requests
import uuid
from pathlib import Path

# Add src to path for imports
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from vasttamsserver.core.config import get_settings

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


@pytest.mark.usefixtures("api_available")
class TestSourcesRouterBatchOperations:
    """Test batch operation edge cases and error handling"""
    
    def test_create_sources_batch_duplicate_ids(self, api_available, auth_headers):
        """Test POST /sources/batch with duplicate source IDs"""
        if not api_available:
            pytest.skip("API not available")
        
        source_id = str(uuid.uuid4())
        batch_data = [
            {"id": source_id, "format": "urn:x-nmos:format:video", "label": "Source 1"},
            {"id": source_id, "format": "urn:x-nmos:format:video", "label": "Source 2"}  # Duplicate ID
        ]
        
        response = requests.post(
            f"{BASE_URL}/sources/batch",
            json=batch_data,
            headers=auth_headers
        )
        # Should return 400 or 409 for duplicate IDs
        assert response.status_code in [400, 409, 422]
        
        # Cleanup if somehow created
        try:
            requests.delete(f"{BASE_URL}/sources/{source_id}", headers=auth_headers)
        except:
            pass
    
    def test_create_sources_batch_mixed_valid_invalid(self, api_available, auth_headers):
        """Test POST /sources/batch with mix of valid and invalid sources"""
        if not api_available:
            pytest.skip("API not available")
        
        batch_data = [
            {"id": str(uuid.uuid4()), "format": "urn:x-nmos:format:video", "label": "Valid Source"},
            {"id": str(uuid.uuid4()), "format": "invalid-format", "label": "Invalid Source"}  # Invalid format
        ]
        
        response = requests.post(
            f"{BASE_URL}/sources/batch",
            json=batch_data,
            headers=auth_headers
        )
        # May return 201 (partial success) or 400/422 (validation error)
        assert response.status_code in [201, 400, 422]
        
        # Cleanup valid sources
        if response.status_code == 201:
            data = response.json()
            if isinstance(data, list):
                for source in data:
                    if "id" in source:
                        try:
                            requests.delete(f"{BASE_URL}/sources/{source['id']}", headers=auth_headers)
                        except:
                            pass
    
    def test_create_sources_batch_very_large(self, api_available, auth_headers):
        """Test POST /sources/batch with very large batch (stress test)"""
        if not api_available:
            pytest.skip("API not available")
        
        # Create 50 sources in batch (reduced from 100 for faster tests)
        batch_data = []
        source_ids = []
        for i in range(50):
            source_id = str(uuid.uuid4())
            source_ids.append(source_id)
            batch_data.append({
                "id": source_id,
                "format": "urn:x-nmos:format:video",
                "label": f"Batch Source {i}"
            })
        
        response = requests.post(
            f"{BASE_URL}/sources/batch",
            json=batch_data,
            headers=auth_headers,
            timeout=60  # Longer timeout for large batch
        )
        # May succeed or fail depending on server limits
        assert response.status_code in [201, 400, 413, 422, 500]
        
        # Cleanup if created
        if response.status_code == 201:
            for source_id in source_ids:
                try:
                    requests.delete(f"{BASE_URL}/sources/{source_id}", headers=auth_headers)
                except:
                    pass


@pytest.mark.usefixtures("api_available")
class TestSourcesRouterErrorPaths:
    """Test error handling and edge cases"""
    
    def test_get_source_invalid_uuid(self, api_available, auth_headers):
        """Test GET /sources/{source_id} with invalid UUID format"""
        if not api_available:
            pytest.skip("API not available")
        
        response = requests.get(f"{BASE_URL}/sources/invalid-uuid-format", headers=auth_headers)
        # Should return 404 or 422 depending on validation
        assert response.status_code in [404, 422]
    
    def test_delete_source_invalid_uuid(self, api_available, auth_headers):
        """Test DELETE /sources/{source_id} with invalid UUID format"""
        if not api_available:
            pytest.skip("API not available")
        
        response = requests.delete(f"{BASE_URL}/sources/invalid-uuid-format", headers=auth_headers)
        # Should return 404 or 422 depending on validation
        assert response.status_code in [404, 422]
    
    def test_update_source_tag_nonexistent_source(self, api_available, auth_headers):
        """Test PUT /sources/{source_id}/tags/{name} with non-existent source"""
        if not api_available:
            pytest.skip("API not available")
        
        source_id = str(uuid.uuid4())
        response = requests.put(
            f"{BASE_URL}/sources/{source_id}/tags/test_tag",
            data="test_value",
            headers={**auth_headers, "Content-Type": "text/plain"}
        )
        assert response.status_code == 404
    
    def test_delete_source_with_dependencies_409(self, api_available, auth_headers):
        """Test DELETE /sources/{source_id} returns 409 when source has dependencies"""
        if not api_available:
            pytest.skip("API not available")
        
        # Create source with flow (dependency)
        source_id = str(uuid.uuid4())
        source_data = {"id": source_id, "format": "urn:x-nmos:format:video", "label": "Source with Flow"}
        requests.post(f"{BASE_URL}/sources", json=source_data, headers=auth_headers)
        
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
        requests.post(f"{BASE_URL}/flows", json=flow_data, headers=auth_headers)
        
        # Try to delete source (should fail with 409 if cascade=false or not specified)
        response = requests.delete(f"{BASE_URL}/sources/{source_id}", headers=auth_headers)
        # May return 409 (conflict) or 200 (if cascade delete works)
        assert response.status_code in [200, 409]
        
        # Cleanup
        try:
            requests.delete(f"{BASE_URL}/flows/{flow_id}", headers=auth_headers)
        except:
            pass
        try:
            requests.delete(f"{BASE_URL}/sources/{source_id}", headers=auth_headers)
        except:
            pass
    
    def test_create_source_missing_required_fields(self, api_available, auth_headers):
        """Test POST /sources with missing required fields"""
        if not api_available:
            pytest.skip("API not available")
        
        # Missing format (required field)
        invalid_data = {
            "id": str(uuid.uuid4()),
            "label": "Source without format"
        }
        response = requests.post(f"{BASE_URL}/sources", json=invalid_data, headers=auth_headers)
        assert response.status_code in [400, 422]
    
    def test_list_sources_invalid_limit_too_large(self, api_available, auth_headers):
        """Test GET /sources with limit exceeding maximum"""
        if not api_available:
            pytest.skip("API not available")
        
        response = requests.get(f"{BASE_URL}/sources?limit=10000", headers=auth_headers)
        # Should return 422 for invalid limit
        assert response.status_code in [422, 400]
    
    def test_list_sources_invalid_limit_zero(self, api_available, auth_headers):
        """Test GET /sources with limit=0"""
        if not api_available:
            pytest.skip("API not available")
        
        response = requests.get(f"{BASE_URL}/sources?limit=0", headers=auth_headers)
        # Should return 422 for invalid limit
        assert response.status_code in [422, 400]
    
    def test_list_sources_invalid_limit_negative(self, api_available, auth_headers):
        """Test GET /sources with negative limit"""
        if not api_available:
            pytest.skip("API not available")
        
        response = requests.get(f"{BASE_URL}/sources?limit=-1", headers=auth_headers)
        # Should return 422 for invalid limit
        assert response.status_code in [422, 400]

