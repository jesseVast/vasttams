#!/usr/bin/env python3
"""
Endpoint CRUD Tests for Sources

Tests the sources endpoint using data from TAMS 8.0 examples.
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
from test_examples import load_example, load_example_list

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
class TestSourceEndpointCRUD:
    """CRUD tests for sources endpoint using TAMS 8.0 example data"""
    
    def test_list_sources_endpoint(self, api_available, auth_headers):
        """Test GET /sources endpoint per TAMS 8.0 spec"""
        if not api_available:
            pytest.skip("API not available")
        
        # Get example list from TAMS 8.0 spec
        expected_sources = load_example_list("sources-get-200.json")
        
        # Call the API
        response = requests.get(f"{BASE_URL}/sources", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        
        # TAMS 8.0 spec: sources endpoint returns objects with expected structure
        if "data" in data and isinstance(data["data"], list):
            sources = data["data"]
            
            # Check structure matches TAMS 8.0 example
            if len(sources) > 0:
                source = sources[0]
                
                # Required fields per TAMS 8.0 spec (source.json)
                assert "id" in source
                assert "format" in source
                
                # Optional but commonly present fields
                if "label" in expected_sources[0]:
                    assert "label" in source or "label" not in expected_sources[0]
                if "description" in expected_sources[0]:
                    assert "description" in source or "description" not in expected_sources[0]
                if "created" in expected_sources[0]:
                    assert "created" in source or "created" not in expected_sources[0]
                if "updated" in expected_sources[0]:
                    assert "updated" in source or "updated" not in expected_sources[0]
    
    def test_get_source_endpoint(self, api_available, auth_headers):
        """Test GET /sources/{id} endpoint per TAMS 8.0 spec"""
        if not api_available:
            pytest.skip("API not available")
        
        # Get example from TAMS 8.0 spec
        example_source = load_example("source-get-200-basic.json")
        
        # First, list to get an existing source ID
        response = requests.get(f"{BASE_URL}/sources", headers=auth_headers)
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, dict) and "data" in data and len(data["data"]) > 0:
                source_id = data["data"][0]["id"]
                
                # Get the specific source
                response = requests.get(f"{BASE_URL}/sources/{source_id}", headers=auth_headers)
                assert response.status_code == 200
                
                source = response.json()
                
                # Verify structure matches TAMS 8.0 example
                assert "id" in source
                assert "format" in source
                
                # Check optional fields that are in the example
                if "label" in example_source:
                    assert "label" in source
                if "description" in example_source:
                    assert "description" in source
    
    def test_create_source_endpoint(self, api_available, auth_headers):
        """Test POST /sources endpoint per TAMS 8.0 spec"""
        if not api_available:
            pytest.skip("API not available")
        
        # Get example from TAMS 8.0 spec
        example_source = load_example("source-get-200-basic.json")
        
        # Create a new source based on example
        import uuid
        source_data = {
            "id": str(uuid.uuid4()),
            "format": example_source["format"],
            "label": f"Test Source from TAMS 8.0 Example"
        }
        
        response = requests.post(f"{BASE_URL}/sources", json=source_data, headers=auth_headers)
        assert response.status_code == 201
        
        created = response.json()
        assert created["id"] == source_data["id"]
        assert created["format"] == example_source["format"]
        
        # Cleanup
        requests.delete(f"{BASE_URL}/sources/{source_data['id']}", headers=auth_headers)
    
    def test_update_source_endpoint(self, api_available, auth_headers):
        """Test PUT /sources/{id} endpoint per TAMS 8.0 spec"""
        if not api_available:
            pytest.skip("API not available")
        
        # Get example from TAMS 8.0 spec
        example_source = load_example("source-get-200-basic.json")
        
        import uuid
        source_id = str(uuid.uuid4())
        
        # Create a source first
        source_data = {
            "id": source_id,
            "format": example_source["format"],
            "label": "Original Label"
        }
        response = requests.post(f"{BASE_URL}/sources", json=source_data, headers=auth_headers)
        assert response.status_code == 201
        
        # TAMS 8.0 uses PUT /sources/{id}/label and /description with query parameters
        updated_label = example_source.get("label", "Updated Label")
        response = requests.put(
            f"{BASE_URL}/sources/{source_id}/label?label={updated_label}",
            headers=auth_headers
        )
        assert response.status_code in [200, 204]
        
        updated_description = example_source.get("description", "Description from TAMS 8.0 example")
        response = requests.put(
            f"{BASE_URL}/sources/{source_id}/description?description={updated_description}",
            headers=auth_headers
        )
        assert response.status_code in [200, 204]
        
        # Verify updates
        response = requests.get(f"{BASE_URL}/sources/{source_id}", headers=auth_headers)
        assert response.status_code == 200
        updated = response.json()
        assert updated.get("label") == updated_label
        assert updated.get("description") == updated_description
        
        # Cleanup
        requests.delete(f"{BASE_URL}/sources/{source_id}", headers=auth_headers)
    
    def test_delete_source_endpoint(self, api_available, auth_headers):
        """Test DELETE /sources/{id} endpoint per TAMS 8.0 spec"""
        if not api_available:
            pytest.skip("API not available")
        
        # Get example from TAMS 8.0 spec
        example_source = load_example("source-get-200-basic.json")
        
        import uuid
        source_id = str(uuid.uuid4())
        
        # Create a source first
        source_data = {
            "id": source_id,
            "format": example_source["format"],
            "label": "Source to Delete"
        }
        response = requests.post(f"{BASE_URL}/sources", json=source_data, headers=auth_headers)
        assert response.status_code == 201
        
        # Delete it
        response = requests.delete(f"{BASE_URL}/sources/{source_id}", headers=auth_headers)
        assert response.status_code in [200, 204]
        
        # Verify deletion
        response = requests.get(f"{BASE_URL}/sources/{source_id}", headers=auth_headers)
        assert response.status_code == 404

