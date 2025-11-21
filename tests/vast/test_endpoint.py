#!/usr/bin/env python3
"""
Endpoint Tests for VAST Vector Operations

Tests the /api/vast/objects endpoints using HTTP requests.
These tests interact with the real API server.
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
BASE_URL = f"http://{settings.host}:{settings.port}/api/tams/latest"
VAST_BASE_URL = f"http://{settings.host}:{settings.port}/api/vast/objects"


def create_mock_vector(dimension=768):
    """Helper to create a mock vector of specified dimension"""
    return [0.1 * i for i in range(dimension)]


@pytest.fixture(scope="module")
def api_available():
    """Check if API server is running"""
    try:
        # Check a valid endpoint instead of root
        response = requests.get(f"{BASE_URL}/sources", timeout=2)
        # Accept any status code except connection errors - server is running
        return response.status_code is not None
    except requests.exceptions.RequestException as e:
        pytest.skip(f"API server not running: {e}. Start server with: python run.py")


# Use auth_headers fixture from conftest.py


@pytest.mark.usefixtures("api_available")
class TestVastVectorEndpoints:
    """HTTP endpoint tests for VAST vector operations"""
    
    def test_update_object_vector_endpoint_success(self, api_available, auth_headers):
        """Test PUT /api/vast/objects/{object_id}/vector endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        # First, create or get an object to update
        # Try to get an existing object
        objects_response = requests.get(f"{BASE_URL}/objects", headers=auth_headers, timeout=10)
        if objects_response.status_code == 200:
            objects = objects_response.json()
            if len(objects) > 0:
                object_id = objects[0]["id"]
            else:
                pytest.skip("No objects available for testing")
        else:
            pytest.skip(f"Could not get objects: {objects_response.status_code}")
        
        # Create a valid 768-dimensional vector
        vector = create_mock_vector(768)
        vector_data = {
            "vector": vector,
            "summary": "Test vector summary",
            "embedding_model": "test-model"
        }
        
        # Call the VAST endpoint
        response = requests.put(
            f"{VAST_BASE_URL}/{object_id}/vector",
            json=vector_data,
            headers=auth_headers,
            timeout=30
        )
        
        # Should return 200 on success
        assert response.status_code in [200, 201], f"Expected 200 or 201, got {response.status_code}: {response.text}"
        
        if response.status_code in [200, 201]:
            result = response.json()
            assert "message" in result
            assert result["object_id"] == object_id
    
    def test_update_object_vector_endpoint_invalid_dimension(self, api_available, auth_headers):
        """Test PUT /api/vast/objects/{object_id}/vector with invalid vector dimension"""
        if not api_available:
            pytest.skip("API not available")
        
        # Get an object ID
        objects_response = requests.get(f"{BASE_URL}/objects", headers=auth_headers, timeout=10)
        if objects_response.status_code == 200:
            objects = objects_response.json()
            if len(objects) > 0:
                object_id = objects[0]["id"]
            else:
                pytest.skip("No objects available for testing")
        else:
            pytest.skip(f"Could not get objects: {objects_response.status_code}")
        
        # Create an invalid vector (wrong dimension)
        vector = create_mock_vector(512)  # Should be 768
        vector_data = {
            "vector": vector,
            "summary": "Test"
        }
        
        # Call the endpoint - should return 422 (validation error) or 400
        response = requests.put(
            f"{VAST_BASE_URL}/{object_id}/vector",
            json=vector_data,
            headers=auth_headers,
            timeout=30
        )
        
        # Pydantic validation happens before endpoint code, so we get 422
        assert response.status_code in [400, 422], f"Expected 400 or 422, got {response.status_code}: {response.text}"
    
    def test_update_object_vector_endpoint_object_not_found(self, api_available, auth_headers):
        """Test PUT /api/vast/objects/{object_id}/vector with non-existent object"""
        if not api_available:
            pytest.skip("API not available")
        
        # Use a non-existent object ID
        object_id = str(uuid.uuid4())
        vector = create_mock_vector(768)
        vector_data = {
            "vector": vector,
            "summary": "Test"
        }
        
        # Call the endpoint
        response = requests.put(
            f"{VAST_BASE_URL}/{object_id}/vector",
            json=vector_data,
            headers=auth_headers,
            timeout=30
        )
        
        # Should return 404
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
    
    def test_search_vectors_endpoint_success(self, api_available, auth_headers):
        """Test POST /api/vast/objects/vector/search endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        # Create a valid query vector
        query_vector = create_mock_vector(768)
        search_data = {
            "vector": query_vector,
            "num_matches": 10,
            "distance_metric": "cosine",
            "distance_numerical_value": 0.75
        }
        
        # Call the search endpoint
        response = requests.post(
            f"{VAST_BASE_URL}/vector/search",
            json=search_data,
            headers=auth_headers,
            timeout=30
        )
        
        # Should return 200 on success
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        if response.status_code == 200:
            result = response.json()
            assert "matches" in result
            assert isinstance(result["matches"], list)
    
    def test_search_vectors_endpoint_invalid_dimension(self, api_available, auth_headers):
        """Test POST /api/vast/objects/vector/search with invalid vector dimension"""
        if not api_available:
            pytest.skip("API not available")
        
        # Create an invalid query vector (wrong dimension)
        query_vector = create_mock_vector(512)  # Should be 768
        search_data = {
            "vector": query_vector
        }
        
        # Call the endpoint - should return 422 (validation error) or 400
        response = requests.post(
            f"{VAST_BASE_URL}/vector/search",
            json=search_data,
            headers=auth_headers,
            timeout=30
        )
        
        # Pydantic validation happens before endpoint code, so we get 422
        assert response.status_code in [400, 422], f"Expected 400 or 422, got {response.status_code}: {response.text}"
    
    def test_search_vectors_endpoint_with_defaults(self, api_available, auth_headers):
        """Test POST /api/vast/objects/vector/search with default parameters"""
        if not api_available:
            pytest.skip("API not available")
        
        # Create a valid query vector with minimal data
        query_vector = create_mock_vector(768)
        search_data = {
            "vector": query_vector
            # num_matches, distance_metric, distance_numerical_value will use defaults
        }
        
        # Call the search endpoint
        response = requests.post(
            f"{VAST_BASE_URL}/vector/search",
            json=search_data,
            headers=auth_headers,
            timeout=30
        )
        
        # Should return 200 on success
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        if response.status_code == 200:
            result = response.json()
            assert "matches" in result
            assert isinstance(result["matches"], list)
    
    def test_search_vectors_endpoint_empty_results(self, api_available, auth_headers):
        """Test POST /api/vast/objects/vector/search returns empty results when no matches"""
        if not api_available:
            pytest.skip("API not available")
        
        # Create a query vector (may not match anything)
        query_vector = create_mock_vector(768)
        search_data = {
            "vector": query_vector,
            "num_matches": 10,
            "distance_metric": "cosine",
            "distance_numerical_value": 0.1  # Very strict threshold
        }
        
        # Call the search endpoint
        response = requests.post(
            f"{VAST_BASE_URL}/vector/search",
            json=search_data,
            headers=auth_headers,
            timeout=30
        )
        
        # Should return 200 even with empty results
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        if response.status_code == 200:
            result = response.json()
            assert "matches" in result
            assert isinstance(result["matches"], list)
            # May be empty if no vectors match the strict threshold

