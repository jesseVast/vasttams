#!/usr/bin/env python3
"""
TAMS 8.0 Compliance Tests for Objects

Tests compliance with TAMS 8.0 specification and app notes.
"""

import pytest
import sys
import requests
from pathlib import Path

# Add src/server to path for imports
server_path = Path(__file__).parent.parent.parent / "src" / "server"
if str(server_path) not in sys.path:
    sys.path.insert(0, str(server_path))

from vasttamsserver.core.config import get_settings
from test_examples import get_objects_example

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
class TestObjectSpecCompliance:
    """Test compliance with TAMS 8.0 object spec"""
    
    def test_object_timerange_per_spec(self, api_available, auth_headers):
        """
        Test object timerange per TAMS 8.0 spec.
        Spec: object.json requires timerange field
        App Note: 0012-using-flow-segment-timeranges
        """
        if not api_available:
            pytest.skip("API not available")
        
        example_object = get_objects_example()
        
        response = requests.get(f"{BASE_URL}/objects", headers=auth_headers)
        if response.status_code == 200:
            objects = response.json()
            
            if len(objects) > 0:
                obj = objects[0]
                
                # TAMS 8.0 requirement: timerange must be present
                assert "timerange" in obj
                
                # Verify timerange structure per spec
                timerange = obj["timerange"]
                
                # Timerange can be string or dict per spec
                assert isinstance(timerange, (str, dict))
                
                # If string, check format (e.g., "[150:0_200:0)")
                if isinstance(timerange, str):
                    # Should contain timestamps
                    assert "_" in timerange or timerange.startswith("[") or timerange.startswith("(")
    
    def test_object_referenced_by_flows(self, api_available, auth_headers):
        """
        Test object referenced_by_flows per TAMS 8.0 spec.
        Spec: object.json requires referenced_by_flows array
        """
        if not api_available:
            pytest.skip("API not available")
        
        example_object = get_objects_example()
        
        response = requests.get(f"{BASE_URL}/objects", headers=auth_headers)
        if response.status_code == 200:
            objects = response.json()
            
            if len(objects) > 0:
                obj = objects[0]
                
                # TAMS 8.0 requirement: referenced_by_flows must be present
                assert "referenced_by_flows" in obj
                assert isinstance(obj["referenced_by_flows"], list)
    
    def test_object_instances_per_adr_0042(self, api_available, auth_headers):
        """
        Test object instances per ADR-0042 (Uncontrolled Object Instance Labels).
        Objects can have multiple instances with labels.
        """
        if not api_available:
            pytest.skip("API not available")
        
        # Get object to test instances
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
                
                # If we have instances, verify structure per ADR-0042
                if len(instances) > 0:
                    instance = instances[0]
                    
                    # Required fields per spec
                    assert "url" in instance
                    
                    # Optional but common fields
                    if "label" in instance:
                        assert isinstance(instance["label"], str)
                    if "storage_id" in instance:
                        assert isinstance(instance["storage_id"], str)
                    if "controlled" in instance:
                        assert isinstance(instance["controlled"], bool)


@pytest.mark.usefixtures("api_available")
class TestObjectAppNoteCompliance:
    """Test compliance with TAMS 8.0 app notes for objects"""
    
    def test_object_timerange_representation_per_appnote_0012(self, api_available, auth_headers):
        """
        Test object timerange representation per App Note 0012.
        Timerange should use string representation with start/end timestamps.
        """
        if not api_available:
            pytest.skip("API not available")
        
        response = requests.get(f"{BASE_URL}/objects", headers=auth_headers)
        if response.status_code == 200:
            objects = response.json()
            
            if len(objects) > 0:
                obj = objects[0]
                
                timerange = obj.get("timerange")
                if timerange and isinstance(timerange, str):
                    # Per App Note 0012, timerange format: "[start_end)"
                    # Should have start and end separated by underscore
                    parts = timerange.split("_")
                    if len(parts) == 2:
                        start = parts[0]
                        end = parts[1]
                        
                        # Start should be inclusive "["
                        assert start.startswith("[")
                        
                        # End should have closing marker
                        assert end.endswith(")") or end.endswith("]")

