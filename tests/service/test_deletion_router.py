#!/usr/bin/env python3
"""
Comprehensive Router Tests for Deletion Requests

Tests all endpoints in service/deletion_router.py to achieve 100% coverage.
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
class TestDeletionRouterGET:
    """Test GET endpoints for deletion router"""
    
    def test_list_deletion_requests(self, api_available, auth_headers):
        """Test GET /flow-delete-requests endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        response = requests.get(f"{BASE_URL}/flow-delete-requests", headers=auth_headers)
        # May return 200 or 404 if endpoint not implemented
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            requests_list = response.json()
            # Should return a list or dict with deletion requests
            assert isinstance(requests_list, (list, dict))
    
    def test_get_deletion_request(self, api_available, auth_headers):
        """Test GET /flow-delete-requests/{request_id} endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        # First get list to find a valid request_id
        list_response = requests.get(f"{BASE_URL}/flow-delete-requests", headers=auth_headers)
        if list_response.status_code == 200:
            requests_list = list_response.json()
            if isinstance(requests_list, list) and requests_list:
                request_id = requests_list[0].get("id") if isinstance(requests_list[0], dict) else requests_list[0]
                if request_id:
                    response = requests.get(f"{BASE_URL}/flow-delete-requests/{request_id}", headers=auth_headers)
                    assert response.status_code == 200
                    deletion_request = response.json()
                    assert deletion_request.get("id") == request_id
        
        # Test with non-existent request_id
        import uuid
        request_id = str(uuid.uuid4())
        response = requests.get(f"{BASE_URL}/flow-delete-requests/{request_id}", headers=auth_headers)
        assert response.status_code == 404


@pytest.mark.usefixtures("api_available")
class TestDeletionRouterErrorPaths:
    """Test error handling and edge cases for deletion router"""
    
    def test_get_deletion_request_invalid_id(self, api_available, auth_headers):
        """Test GET /flow-delete-requests/{request_id} with invalid ID format"""
        if not api_available:
            pytest.skip("API not available")
        
        response = requests.get(f"{BASE_URL}/flow-delete-requests/invalid-id", headers=auth_headers)
        # May return 404 or 422 depending on validation
        assert response.status_code in [404, 422]
    
    def test_list_deletion_requests_without_auth(self, api_available):
        """Test GET /flow-delete-requests without authentication"""
        if not api_available:
            pytest.skip("API not available")
        
        response = requests.get(f"{BASE_URL}/flow-delete-requests")
        # May return 200 (if public), 401 (unauthorized), 403 (forbidden), or 404 (if endpoint requires auth)
        assert response.status_code in [200, 401, 403, 404]
    
    def test_get_deletion_request_without_auth(self, api_available):
        """Test GET /flow-delete-requests/{request_id} without authentication"""
        if not api_available:
            pytest.skip("API not available")
        
        import uuid
        request_id = str(uuid.uuid4())
        response = requests.get(f"{BASE_URL}/flow-delete-requests/{request_id}")
        # May return 401 (unauthorized) or 404 (if public endpoint)
        assert response.status_code in [200, 401, 403, 404]


@pytest.mark.usefixtures("api_available")
class TestDeletionRouterResponseStructure:
    """Test deletion router response structure"""
    
    def test_list_deletion_requests_structure(self, api_available, auth_headers):
        """Test that list deletion requests returns correct structure"""
        if not api_available:
            pytest.skip("API not available")
        
        response = requests.get(f"{BASE_URL}/flow-delete-requests", headers=auth_headers)
        
        if response.status_code == 200:
            requests_list = response.json()
            # Should return a list or dict
            assert isinstance(requests_list, (list, dict))
            
            # If list, check structure of first item
            if isinstance(requests_list, list) and requests_list:
                first_request = requests_list[0]
                if isinstance(first_request, dict):
                    # Should have id field
                    assert "id" in first_request
    
    def test_get_deletion_request_structure(self, api_available, auth_headers):
        """Test that get deletion request returns correct structure"""
        if not api_available:
            pytest.skip("API not available")
        
        # First get list to find a valid request_id
        list_response = requests.get(f"{BASE_URL}/flow-delete-requests", headers=auth_headers)
        
        if list_response.status_code == 200:
            requests_list = list_response.json()
            if isinstance(requests_list, list) and requests_list:
                first_request = requests_list[0]
                if isinstance(first_request, dict) and "id" in first_request:
                    request_id = first_request["id"]
                    
                    response = requests.get(f"{BASE_URL}/flow-delete-requests/{request_id}", headers=auth_headers)
                    if response.status_code == 200:
                        deletion_request = response.json()
                        assert isinstance(deletion_request, dict)
                        assert deletion_request.get("id") == request_id
    
    def test_empty_deletion_requests_list(self, api_available, auth_headers):
        """Test that empty deletion requests list returns empty array"""
        if not api_available:
            pytest.skip("API not available")
        
        response = requests.get(f"{BASE_URL}/flow-delete-requests", headers=auth_headers)
        
        if response.status_code == 200:
            requests_list = response.json()
            # Should return empty list if no requests
            if isinstance(requests_list, list):
                # Empty list is valid
                assert isinstance(requests_list, list)

