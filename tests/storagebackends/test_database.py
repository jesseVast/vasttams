#!/usr/bin/env python3
"""
Database Integration Tests for Storage Backends

Tests that interact with a running TAMS server and real VAST database.
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
class TestStorageBackendDatabaseIntegration:
    """Integration tests for Storage Backends against real database"""
    
    def test_create_storage_backend_in_database(self, api_available):
        """Test creating a storage backend in the database"""
        if not api_available:
            pytest.skip("API not available")
        
        backend_id = None
        
        try:
            # Create a storage backend via API
            backend_data = {
                "label": f"database-test-{uuid.uuid4()}",
                "store_type": "http_object_store",
                "provider": "aws",
                "store_product": "s3",
                "region": "us-east-1",
                "availability_zone": "a",
                "default_storage": False
            }
            
            headers = _login_admin_headers()
            response = requests.post(f"{BASE_URL}/service/storage-backends", json=backend_data, headers=headers)
            assert response.status_code == 201, f"Failed to create backend: {response.text}"
            
            created = response.json()
            backend_id = created["id"]
            
            # Verify it's in the database
            get_response = requests.get(f"{BASE_URL}/service/storage-backends/{backend_id}", headers=headers)
            assert get_response.status_code == 200
            
            retrieved = get_response.json()
            assert retrieved["label"] == backend_data["label"]
            assert retrieved["provider"] == backend_data["provider"]
            assert retrieved["region"] == backend_data["region"]
            assert retrieved["default_storage"] == False
            
        finally:
            # Cleanup
            if backend_id:
                requests.delete(f"{BASE_URL}/service/storage-backends/{backend_id}", headers=headers)
    
    def test_list_storage_backends_from_database(self, api_available):
        """Test listing storage backends from the database"""
        if not api_available:
            pytest.skip("API not available")
        
        headers = _login_admin_headers()
        response = requests.get(f"{BASE_URL}/service/storage-backends", headers=headers)
        assert response.status_code == 200
        
        backends = response.json()
        assert isinstance(backends, list)
        
        # Verify structure
        if backends:
            backend = backends[0]
            assert "id" in backend
            assert "store_type" in backend
            assert "provider" in backend
    
    def test_update_storage_backend_in_database(self, api_available):
        """Test updating a storage backend in the database"""
        if not api_available:
            pytest.skip("API not available")
        
        backend_id = None
        
        try:
            # Create backend
            backend_data = {
                "label": f"update-test-{uuid.uuid4()}",
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
            
            # Update backend
            update_data = {
                "label": "updated-label",
                "region": "eu-west-1"
            }
            
            update_response = requests.put(
                f"{BASE_URL}/service/storage-backends/{backend_id}",
                json=update_data,
                headers=headers
            )
            assert update_response.status_code == 200
            
            # Verify update persisted
            get_response = requests.get(f"{BASE_URL}/service/storage-backends/{backend_id}", headers=headers)
            assert get_response.status_code == 200
            
            updated = get_response.json()
            assert updated["label"] == "updated-label"
            assert updated["region"] == "eu-west-1"
            
        finally:
            # Cleanup
            if backend_id:
                requests.delete(f"{BASE_URL}/service/storage-backends/{backend_id}", headers=headers)

