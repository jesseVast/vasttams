#!/usr/bin/env python3
"""
CRUD Tests for Storage Backends Endpoint

Tests Create, Read, Update, Delete operations for storage backends.
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


def _login_admin_headers():
    resp = requests.post(
        f"{BASE_URL}/auth/login",
        json={"username": "admin", "password": "vastdata"}
    )
    if resp.status_code != 200:
        return {}
    token = resp.json().get("access_token")
    return {"Authorization": f"Bearer {token}"} if token else {}


@pytest.fixture(scope="module")
def api_available():
    """Check if API server is running"""
    try:
        response = requests.get(f"{BASE_URL}/", timeout=2)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        pytest.skip("API server not running. Start server with: python run.py")


@pytest.mark.usefixtures("api_available")
class TestStorageBackendCRUD:
    """Complete CRUD tests for Storage Backends endpoint"""
    
    def test_create_storage_backend(self, api_available):
        """Test CREATE operation - POST /service/storage-backends"""
        if not api_available:
            pytest.skip("API not available")
        
        backend_data = {
            "label": f"test-backend-{uuid.uuid4()}",
            "store_type": "http_object_store",
            "provider": "minio",
            "store_product": "minio",
            "region": "us-east-1",
            "availability_zone": "a",
            "default_storage": False
        }
        
        headers = _login_admin_headers()
        response = requests.post(f"{BASE_URL}/service/storage-backends", json=backend_data, headers=headers)
        
        # Should succeed or return 422 if validation fails
        assert response.status_code in [201, 422], \
            f"Failed to create storage backend: {response.text}"
        
        if response.status_code == 201:
            created = response.json()
            assert "id" in created
            assert created["label"] == backend_data["label"]
            
            # Cleanup
            backend_id = created["id"]
            delete_response = requests.delete(f"{BASE_URL}/service/storage-backends/{backend_id}", headers=headers)
            assert delete_response.status_code in [204, 404]
    
    def test_get_storage_backends(self, api_available):
        """Test READ operation - GET /service/storage-backends"""
        if not api_available:
            pytest.skip("API not available")
        
        headers = _login_admin_headers()
        response = requests.get(f"{BASE_URL}/service/storage-backends", headers=headers)
        assert response.status_code == 200
        
        backends = response.json()
        assert isinstance(backends, list)
        
        # Should have at least one backend (default or created)
        assert len(backends) >= 1
    
    def test_update_storage_backend(self, api_available):
        """Test UPDATE operation - PUT /service/storage-backends/{id}"""
        if not api_available:
            pytest.skip("API not available")
        
        # Create a test backend
        backend_data = {
            "label": f"test-backend-{uuid.uuid4()}",
            "store_type": "http_object_store",
            "provider": "minio",
            "store_product": "minio",
            "region": "us-east-1"
        }
        
        headers = _login_admin_headers()
        create_response = requests.post(
            f"{BASE_URL}/service/storage-backends",
            json=backend_data,
            headers=headers
        )
        
        if create_response.status_code != 201:
            pytest.skip("Could not create test backend")
        
        created = create_response.json()
        backend_id = created["id"]
        
        try:
            # Get initial state
            get_response = requests.get(f"{BASE_URL}/service/storage-backends/{backend_id}", headers=headers)
            assert get_response.status_code == 200
            initial = get_response.json()
            
            # Update the backend - only editable fields are: endpoint_url, use_ssl, access_key, secret_key, bucket_name, root_path
            # Note: label is NOT editable per StorageBackendPatch model
            update_data = {
                "endpoint_url": "https://updated.example.com" if initial.get("endpoint_url") != "https://updated.example.com" else "https://updated2.example.com",
                "use_ssl": not initial.get("use_ssl", False)
            }
            
            update_response = requests.put(
                f"{BASE_URL}/service/storage-backends/{backend_id}",
                json=update_data,
                headers=headers
            )
            assert update_response.status_code == 200, \
                f"Failed to update storage backend: {update_response.text}"
            
            # Verify update
            get_response = requests.get(f"{BASE_URL}/service/storage-backends/{backend_id}", headers=headers)
            assert get_response.status_code == 200
            
            updated = get_response.json()
            assert updated["endpoint_url"] == update_data["endpoint_url"]
            assert updated["use_ssl"] == update_data["use_ssl"]
            
        finally:
            # Cleanup
            requests.delete(f"{BASE_URL}/service/storage-backends/{backend_id}", headers=headers)
    
    def test_delete_storage_backend(self, api_available):
        """Test DELETE operation - DELETE /service/storage-backends/{id}"""
        if not api_available:
            pytest.skip("API not available")
        
        # Create a test backend
        backend_data = {
            "label": f"test-backend-{uuid.uuid4()}",
            "store_type": "http_object_store",
            "provider": "minio",
            "store_product": "minio",
            "region": "us-east-1",
            "default_storage": False
        }
        
        headers = _login_admin_headers()
        create_response = requests.post(
            f"{BASE_URL}/service/storage-backends",
            json=backend_data,
            headers=headers
        )
        
        if create_response.status_code != 201:
            pytest.skip("Could not create test backend")
        
        created = create_response.json()
        backend_id = created["id"]
        
        # Delete the backend
        delete_response = requests.delete(f"{BASE_URL}/service/storage-backends/{backend_id}", headers=headers)
        assert delete_response.status_code == 204, \
            f"Failed to delete storage backend: {delete_response.text}"
        
        # Verify deletion
        get_response = requests.get(f"{BASE_URL}/service/storage-backends/{backend_id}", headers=headers)
        assert get_response.status_code == 404

