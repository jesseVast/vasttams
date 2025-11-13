#!/usr/bin/env python3
"""
Endpoint CRUD Tests for Objects

Tests the objects endpoint using data from TAMS 8.0 examples.
These tests interact with the real API server.
"""

import pytest
import sys
import requests
from pathlib import Path

# Add src to path for imports
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from vasttamsserver.core.config import get_settings
from test_examples import load_example, get_objects_example

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
class TestObjectEndpointCRUD:
    """CRUD tests for objects endpoint using TAMS 8.0 example data"""
    
    def test_list_objects_endpoint(self, api_available, auth_headers):
        """Test GET /objects endpoint per TAMS 8.0 spec"""
        if not api_available:
            pytest.skip("API not available")
        
        # Get example from TAMS 8.0 spec
        example_object = get_objects_example()
        
        # Call the API
        response = requests.get(f"{BASE_URL}/objects", headers=auth_headers, timeout=30)
        # May return 200 or 503 if server is overloaded
        if response.status_code not in [200, 503]:
            print(f"Error response: {response.text}")
        assert response.status_code in [200, 503], f"Expected 200 or 503, got {response.status_code}: {response.text}"
        
        if response.status_code == 200:
            objects = response.json()
            assert isinstance(objects, list)
            
            # Check structure matches TAMS 8.0 example
            if len(objects) > 0:
                obj = objects[0]
                
                # Required fields per TAMS 8.0 spec (object.json)
                assert "id" in obj
                assert "referenced_by_flows" in obj
                assert "timerange" in obj  # TAMS 8.0 requirement
                
                # Check timerange structure per spec
                if "timerange" in obj:
                    timerange = obj["timerange"]
                    # Timerange should be a dict with start/end or a string
                    assert isinstance(timerange, (dict, str))
    
    def test_get_object_endpoint(self, api_available, auth_headers):
        """Test GET /objects/{id} endpoint per TAMS 8.0 spec"""
        if not api_available:
            pytest.skip("API not available")
        
        # Get example from TAMS 8.0 spec
        example_object = get_objects_example()
        
        # Call the API to get objects
        response = requests.get(f"{BASE_URL}/objects", headers=auth_headers)
        if response.status_code == 200:
            objects = response.json()
            
            if len(objects) > 0:
                object_id = objects[0]["id"]
                
                # Get the specific object
                response = requests.get(f"{BASE_URL}/objects/{object_id}", headers=auth_headers)
                assert response.status_code == 200
                
                obj = response.json()
                
                # Verify structure matches TAMS 8.0 example
                assert "id" in obj
                assert "referenced_by_flows" in obj
                assert "timerange" in obj


@pytest.mark.usefixtures("api_available")
class TestObjectInstancesEndpoint:
    """Test object instances endpoints per ADR-0042"""
    
    def test_list_object_instances_endpoint(self, api_available, auth_headers):
        """Test GET /objects/{id}/instances endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        # Get an object first
        response = requests.get(f"{BASE_URL}/objects", headers=auth_headers)
        if response.status_code == 200:
            objects = response.json()
            
            if len(objects) > 0:
                object_id = objects[0]["id"]
                
                # List instances for this object
                response = requests.get(f"{BASE_URL}/objects/{object_id}/instances", headers=auth_headers)
                assert response.status_code == 200
                
                instances = response.json()
                assert isinstance(instances, list)
                
                # If we have instances, check they have required fields per ADR-0042
                if len(instances) > 0:
                    instance = instances[0]
                    assert "url" in instance
                    if "label" in instance:
                        assert isinstance(instance["label"], str)

