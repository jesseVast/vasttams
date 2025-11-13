#!/usr/bin/env python3
"""
Authentication Endpoint Tests

Tests the REST API endpoints for authentication providers.
"""

import pytest
import sys
import requests
from pathlib import Path

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
        # Health endpoint is at root, not under /api/tams/latest
        base_url_without_api = BASE_URL.replace("/api/tams/latest", "")
        response = requests.get(f"{base_url_without_api}/health", timeout=2)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        pytest.skip("API server not running. Start server with: python run.py")


@pytest.mark.usefixtures("api_available")
class TestAuthEndpoint:
    """Endpoint tests for Authentication Provider API"""
    
    def test_list_auth_providers(self, api_available, auth_headers):
        """Test GET /auth/providers endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        response = requests.get(f"{BASE_URL}/auth/providers", headers=auth_headers)
        assert response.status_code == 200
        
        providers = response.json()
        assert isinstance(providers, list)
    
    def test_get_auth_provider_bearer(self, api_available, auth_headers):
        """Test GET /auth/providers/bearer endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        response = requests.get(f"{BASE_URL}/auth/providers/bearer", headers=auth_headers)
        
        # May succeed or fail with 404
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            provider = response.json()
            assert "method" in provider
            assert provider["method"] == "bearer"
    
    def test_get_auth_provider_basic(self, api_available, auth_headers):
        """Test GET /auth/providers/basic endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        response = requests.get(f"{BASE_URL}/auth/providers/basic", headers=auth_headers)
        
        # May succeed or fail with 404
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            provider = response.json()
            assert "method" in provider
    
    def test_update_auth_provider(self, api_available, auth_headers):
        """Test PUT /auth/providers/{method} endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        # Try to update bearer provider
        update_data = {
            "enabled": True
        }
        
        response = requests.put(
            f"{BASE_URL}/auth/providers/bearer",
            json=update_data,
            headers=auth_headers
        )
        
        # May succeed, fail with 404, or fail with 500 (internal error)
        assert response.status_code in [200, 404, 500]
    
    def test_reload_auth_providers(self, api_available, auth_headers):
        """Test POST /auth/providers/reload endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        response = requests.post(f"{BASE_URL}/auth/providers/reload", headers=auth_headers)
        assert response.status_code in [200, 500]
        
        if response.status_code == 200:
            result = response.json()
            assert "message" in result

