#!/usr/bin/env python3
"""
Endpoint CRUD Tests for Flows

Tests the flows endpoint using data from TAMS 8.0 examples.
These tests interact with the real API server.
"""

import pytest
import sys
import requests
from pathlib import Path

# Add src to path for imports
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from vasttams.core.config import get_settings
from test_examples import load_example, get_video_flow_example, get_vfr_flow_example

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
def test_source_id(api_available):
    """Create a test source for flow testing"""
    if not api_available:
        pytest.skip("API not available")
    
    import uuid
    source_id = str(uuid.uuid4())
    source_data = {
        "id": source_id,
        "format": "urn:x-nmos:format:video",
        "label": f"Test Source {source_id[:8]}"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/sources", json=source_data)
        if response.status_code == 201:
            yield source_id
        else:
            pytest.skip(f"Failed to create test source: {response.text}")
    finally:
        # Cleanup
        requests.delete(f"{BASE_URL}/sources/{source_id}")


@pytest.mark.usefixtures("api_available")
class TestFlowEndpointCRUD:
    """CRUD tests for flows endpoint using TAMS 8.0 example data"""
    
    def test_list_flows_endpoint(self, api_available):
        """Test GET /flows endpoint per TAMS 8.0 spec"""
        if not api_available:
            pytest.skip("API not available")
        
        # Get example from TAMS 8.0 spec
        from test_examples import load_example_list
        expected_flows = load_example_list("flows-get-200.json")
        
        # Call the API
        response = requests.get(f"{BASE_URL}/flows")
        assert response.status_code == 200
        
        data = response.json()
        
        # TAMS 8.0 spec: flows endpoint returns objects with expected structure
        if "data" in data and isinstance(data["data"], list):
            flows = data["data"]
            
            # Check structure matches TAMS 8.0 example
            if len(flows) > 0:
                flow = flows[0]
                
                # Required fields per TAMS 8.0 spec (flow.json)
                assert "id" in flow
                assert "source_id" in flow
                assert "format" in flow
                
                # Check optional but commonly present fields
                if expected_flows and len(expected_flows) > 0:
                    example_flow = expected_flows[0]
                    if "codec" in example_flow:
                        assert "codec" in flow or "codec" not in example_flow
                    if "label" in example_flow:
                        assert "label" in flow or "label" not in example_flow
    
    def test_get_flow_endpoint(self, api_available, test_source_id):
        """Test GET /flows/{id} endpoint per TAMS 8.0 spec"""
        if not api_available:
            pytest.skip("API not available")
        
        # Get example from TAMS 8.0 spec
        example_flow = get_video_flow_example()
        
        import uuid
        flow_id = str(uuid.uuid4())
        
        # Create a flow based on example
        flow_data = {
            "id": flow_id,
            "source_id": test_source_id,
            "format": example_flow["format"],
            "codec": example_flow["codec"],
            "label": example_flow.get("label", "Test Flow"),
            "essence_parameters": example_flow["essence_parameters"]
        }
        
        response = requests.post(f"{BASE_URL}/flows", json=flow_data)
        if response.status_code == 201:
            # Get the created flow
            response = requests.get(f"{BASE_URL}/flows/{flow_id}")
            assert response.status_code == 200
            
            flow = response.json()
            
            # Verify structure matches TAMS 8.0 example
            assert "id" in flow
            assert "source_id" in flow
            assert "format" in flow
            
            # Cleanup
            requests.delete(f"{BASE_URL}/flows/{flow_id}")
    
    def test_create_video_flow_from_example(self, api_available, test_source_id):
        """Test POST /flows with video flow from TAMS 8.0 example"""
        if not api_available:
            pytest.skip("API not available")
        
        # Get video flow example
        example_flow = get_video_flow_example()
        
        import uuid
        flow_data = {
            "id": str(uuid.uuid4()),
            "source_id": test_source_id,
            "format": example_flow["format"],
            "codec": example_flow["codec"],
            "label": example_flow.get("label", "Video Flow from Example"),
            "essence_parameters": example_flow["essence_parameters"]
        }
        
        response = requests.post(f"{BASE_URL}/flows", json=flow_data)
        assert response.status_code == 201
        
        created = response.json()
        assert created["id"] == flow_data["id"]
        assert created["source_id"] == test_source_id
        
        # Cleanup
        requests.delete(f"{BASE_URL}/flows/{flow_data['id']}")
    
    def test_create_vfr_flow_from_example(self, api_available, test_source_id):
        """Test POST /flows with VFR flow from TAMS 8.0 example (vfr=true)"""
        if not api_available:
            pytest.skip("API not available")
        
        # Get VFR flow example
        example_flow = get_vfr_flow_example()
        
        import uuid
        flow_data = {
            "id": str(uuid.uuid4()),
            "source_id": test_source_id,
            "format": example_flow["format"],
            "codec": example_flow["codec"],
            "label": example_flow.get("label", "VFR Flow from Example"),
            "essence_parameters": example_flow["essence_parameters"]
        }
        
        response = requests.post(f"{BASE_URL}/flows", json=flow_data)
        assert response.status_code == 201
        
        created = response.json()
        assert created["id"] == flow_data["id"]
        
        # Cleanup
        requests.delete(f"{BASE_URL}/flows/{flow_data['id']}")

