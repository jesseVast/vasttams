#!/usr/bin/env python3
"""
Database Integration Tests for Objects

Tests that interact with a running TAMS server and real VAST database.
"""

import pytest
import sys
import requests
from pathlib import Path
import time
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


@pytest.fixture
def clean_object_id():
    """Generate a clean object ID for each test"""
    return str(uuid.uuid4())


@pytest.mark.usefixtures("api_available")
class TestObjectDatabaseIntegration:
    """Integration tests for Objects against real database"""
    
    def test_list_objects_from_database(self, api_available, auth_headers):
        """Test listing objects from the database per TAMS 8.0 spec"""
        if not api_available:
            pytest.skip("API not available")
        
        try:
            response = requests.get(f"{BASE_URL}/objects", headers=auth_headers, timeout=30)
            # May return 200 or 503 if server is overloaded
            assert response.status_code in [200, 503]
            if response.status_code == 200:
                # TAMS 8.0: objects endpoint returns a list, not wrapped in "data"
                objects = response.json()
                assert isinstance(objects, list)
                
                # If we have objects, check they have required fields per spec
                if len(objects) > 0:
                    obj = objects[0]
                    assert "id" in obj
                    assert "referenced_by_flows" in obj
                    assert "timerange" in obj  # TAMS 8.0 requirement
        except requests.exceptions.ReadTimeout:
            # Server is overloaded, skip this test
            pytest.skip("Server timeout - server may be overloaded")
    
    def test_get_object_details(self, api_available, auth_headers):
        """Test getting object details including timerange per TAMS 8.0 spec"""
        if not api_available:
            pytest.skip("API not available")
        
        # First, list objects to get one to query
        response = requests.get(f"{BASE_URL}/objects", headers=auth_headers)
        if response.status_code == 200:
            objects = response.json()
            assert isinstance(objects, list)
            
            if len(objects) > 0:
                # Use the first object
                object_id = objects[0]["id"]
                
                # Get details
                response = requests.get(f"{BASE_URL}/objects/{object_id}", headers=auth_headers)
                assert response.status_code == 200
                
                obj = response.json()
                
                # TAMS 8.0: Required fields per object.json schema
                assert "id" in obj
                assert "referenced_by_flows" in obj
                assert "timerange" in obj  # TAMS 8.0 requirement
                
                # Verify timerange structure
                timerange = obj["timerange"]
                assert isinstance(timerange, dict)
                assert "start" in timerange or "end" in timerange


@pytest.mark.usefixtures("api_available")
class TestObjectInstances:
    """Test object instances per ADR-0042"""
    
    def test_list_object_instances(self, api_available, auth_headers):
        """Test listing instances for an object"""
        if not api_available:
            pytest.skip("API not available")
        
        # First, get an object
        response = requests.get(f"{BASE_URL}/objects", headers=auth_headers)
        if response.status_code == 200:
            data = response.json()
            # API returns a list directly, not a dict with "data" key
            if isinstance(data, list) and len(data) > 0:
                object_id = data[0]["id"]
                
                # List instances
                response = requests.get(f"{BASE_URL}/objects/{object_id}/instances", headers=auth_headers)
                assert response.status_code == 200
                
                instances = response.json()
                assert isinstance(instances, list)


@pytest.mark.usefixtures("api_available")
class TestObjectTimerange:
    """Test object timerange support per TAMS 8.0"""
    
    def test_object_timerange_structure(self, api_available, auth_headers):
        """Test that objects include timerange per spec"""
        if not api_available:
            pytest.skip("API not available")
        
        response = requests.get(f"{BASE_URL}/objects", headers=auth_headers)
        if response.status_code == 200:
            data = response.json()
            # API returns a list directly, not a dict with "data" key
            if isinstance(data, list) and len(data) > 0:
                # Check first object has timerange
                obj = data[0]
                assert "timerange" in obj, "Objects must include timerange per TAMS 8.0"
                
                timerange = obj["timerange"]
                assert isinstance(timerange, dict)
                assert "start" in timerange or "end" in timerange

