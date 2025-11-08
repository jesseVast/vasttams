#!/usr/bin/env python3
"""
TAMS 8.0 Compliance Tests for Storage Backends

Tests compliance with TAMS 8.0 specification (ADR0032, ADR0038).
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
class TestStorageBackendSpecCompliance:
    """Test storage backend compliance with TAMS 8.0 specification"""
    
    def test_storage_backends_schema_compliance(self, api_available, auth_headers):
        """Test that storage backends schema matches TAMS 8.0 spec"""
        if not api_available:
            pytest.skip("API not available")
        
        response = requests.get(f"{BASE_URL}/service/storage-backends", headers=auth_headers)
        assert response.status_code == 200
        
        backends = response.json()
        assert isinstance(backends, list), "Storage backends should be a list"
        
        if backends:
            backend = backends[0]
            # Required fields per TAMS 8.0 spec
            assert "id" in backend, "Storage backend must have 'id' field"
            assert "store_type" in backend, "Storage backend must have 'store_type' field"
            assert "provider" in backend, "Storage backend must have 'provider' field"
            assert "store_product" in backend, "Storage backend must have 'store_product' field"
            
            # Optional but important fields
            assert "default_storage" in backend or backend.get("default_storage") is not None
    
    def test_storage_backend_store_type_compliance(self, api_available, auth_headers):
        """Test that store_type is valid per TAMS 8.0 spec"""
        if not api_available:
            pytest.skip("API not available")
        
        response = requests.get(f"{BASE_URL}/service/storage-backends", headers=auth_headers)
        if response.status_code == 200:
            backends = response.json()
            
            for backend in backends:
                store_type = backend.get("store_type")
                assert store_type in ["http_object_store"], \
                    f"Invalid store_type: {store_type}. Must be 'http_object_store'"
    
    def test_storage_backend_id_format(self, api_available, auth_headers):
        """Test that storage backend IDs are valid UUIDs"""
        if not api_available:
            pytest.skip("API not available")
        
        response = requests.get(f"{BASE_URL}/service/storage-backends", headers=auth_headers)
        if response.status_code == 200:
            backends = response.json()
            
            for backend in backends:
                backend_id = backend.get("id")
                # UUID validation
                try:
                    uuid.UUID(backend_id)
                except ValueError:
                    pytest.fail(f"Invalid UUID format for storage backend ID: {backend_id}")


@pytest.mark.usefixtures("api_available")
class TestStorageBackendAppNoteCompliance:
    """Test compliance with TAMS appnotes related to storage backends"""
    
    def test_storage_backend_advertising(self, api_available, auth_headers):
        """Test that storage backends are advertised per ADR0032"""
        if not api_available:
            pytest.skip("API not available")
        
        # Get storage backends
        response = requests.get(f"{BASE_URL}/service/storage-backends", headers=auth_headers)
        assert response.status_code == 200
        
        backends = response.json()
        
        # Should have at least one backend (default or configured)
        assert len(backends) >= 1, "At least one storage backend should be advertised"
        
        # Check for default backend
        default_backends = [b for b in backends if b.get("default_storage", False)]
        # Note: It's valid to have zero or one default backend per spec

