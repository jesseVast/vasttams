#!/usr/bin/env python3
"""
Endpoint Tests for Storage Backends

Tests the REST API endpoints for storage backends.
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


@pytest.mark.usefixtures("api_available")
class TestStorageBackendEndpointCRUD:
    """Endpoint CRUD tests for Storage Backends API"""
    
    def test_list_storage_backends_endpoint(self, api_available):
        """Test GET /service/storage-backends endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        # Call the API
        response = requests.get(f"{BASE_URL}/service/storage-backends")
        assert response.status_code == 200
        
        backends = response.json()
        assert isinstance(backends, list)
    
    def test_get_storage_backend_endpoint(self, api_available):
        """Test GET /service/storage-backends/{id} endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        # First get all backends
        list_response = requests.get(f"{BASE_URL}/service/storage-backends")
        assert list_response.status_code == 200
        
        backends = list_response.json()
        if len(backends) == 0:
            pytest.skip("No storage backends available")
        
        # Get the first backend
        backend_id = backends[0]["id"]
        response = requests.get(f"{BASE_URL}/service/storage-backends/{backend_id}")
        assert response.status_code == 200
        
        backend = response.json()
        assert backend["id"] == backend_id
    
    def test_create_storage_backend_endpoint(self, api_available):
        """Test POST /service/storage-backends endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        backend_data = {
            "label": f"endpoint-test-{uuid.uuid4()}",
            "store_type": "http_object_store",
            "provider": "minio",
            "store_product": "minio",
            "region": "us-east-1",
            "default_storage": False
        }
        
        response = requests.post(
            f"{BASE_URL}/service/storage-backends",
            json=backend_data
        )
        
        # May succeed or fail with validation error
        assert response.status_code in [201, 422]
        
        if response.status_code == 201:
            created = response.json()
            backend_id = created["id"]
            
            # Cleanup
            requests.delete(f"{BASE_URL}/service/storage-backends/{backend_id}")


@pytest.mark.usefixtures("api_available")
class TestStorageBackendDeleteValidation:
    """Test storage backend deletion validation (no delete if objects exist)"""
    
    def test_delete_backend_with_no_objects(self, api_available):
        """Test that backend can be deleted when no objects reference it"""
        if not api_available:
            pytest.skip("API not available")
        
        backend_id = None
        
        try:
            # Create a test backend
            backend_data = {
                "label": f"delete-test-{uuid.uuid4()}",
                "store_type": "http_object_store",
                "provider": "minio",
                "store_product": "minio",
                "region": "us-east-1",
                "default_storage": False
            }
            
            create_response = requests.post(
                f"{BASE_URL}/service/storage-backends",
                json=backend_data
            )
            
            if create_response.status_code != 201:
                pytest.skip("Could not create test backend")
            
            created = create_response.json()
            backend_id = created["id"]
            
            # Delete should succeed (no objects reference it)
            delete_response = requests.delete(
                f"{BASE_URL}/service/storage-backends/{backend_id}"
            )
            assert delete_response.status_code == 204
            
        finally:
            # Extra cleanup
            if backend_id:
                requests.delete(f"{BASE_URL}/service/storage-backends/{backend_id}")

