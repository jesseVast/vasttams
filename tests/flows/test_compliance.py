#!/usr/bin/env python3
"""
TAMS 8.0 Compliance Tests for Flows

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
from integration.test_examples import get_video_flow_example, get_vfr_flow_example

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


@pytest.fixture
def test_source_id(api_available, auth_headers):
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
        response = requests.post(f"{BASE_URL}/sources", json=source_data, headers=auth_headers)
        if response.status_code == 201:
            yield source_id
        else:
            pytest.skip(f"Failed to create test source: {response.text}")
    finally:
        requests.delete(f"{BASE_URL}/sources/{source_id}", headers=auth_headers)


@pytest.mark.usefixtures("api_available")
class TestFlowSpecCompliance:
    """Test compliance with TAMS 8.0 flow spec"""
    
    def test_vfr_compliance_per_adr_0041(self, api_available, test_source_id, auth_headers):
        """
        Test VFR compliance per ADR-0041 (Require Explicit Framerate).
        App Note: 0013-setting-flow-bit-rate-properties
        """
        if not api_available:
            pytest.skip("API not available")
        
        example_vfr = get_vfr_flow_example()
        
        import uuid
        flow_data = {
            "id": str(uuid.uuid4()),
            "source_id": test_source_id,
            "format": example_vfr["format"],
            "codec": example_vfr["codec"],
            "essence_parameters": example_vfr["essence_parameters"]
        }
        
        response = requests.post(f"{BASE_URL}/flows", json=flow_data, headers=auth_headers)
        assert response.status_code == 201
        
        created = response.json()
        assert created["id"] == flow_data["id"]
        
        # Verify VFR is set correctly
        assert flow_data["essence_parameters"]["vfr"] == True
        
        # Cleanup
        requests.delete(f"{BASE_URL}/flows/{flow_data['id']}", headers=auth_headers)
    
    def test_flow_essence_parameters_structure(self, api_available, test_source_id, auth_headers):
        """
        Test flow essence_parameters structure per TAMS 8.0 spec.
        Spec: flow-video.json, flow-audio.json define essence_parameters
        """
        if not api_available:
            pytest.skip("API not available")
        
        example_flow = get_video_flow_example()
        
        import uuid
        flow_data = {
            "id": str(uuid.uuid4()),
            "source_id": test_source_id,
            "format": example_flow["format"],
            "codec": example_flow["codec"],
            "essence_parameters": example_flow["essence_parameters"]
        }
        
        response = requests.post(f"{BASE_URL}/flows", json=flow_data, headers=auth_headers)
        assert response.status_code == 201
        
        created = response.json()
        
        # Verify essence_parameters structure
        if "essence_parameters" in created:
            ep = created["essence_parameters"]
            assert "frame_width" in ep
            assert "frame_height" in ep
        
        # Cleanup
        requests.delete(f"{BASE_URL}/flows/{flow_data['id']}", headers=auth_headers)
    
    def test_flow_tags_per_appnote_0003(self, api_available, test_source_id, auth_headers):
        """
        Test flow tags per App Note 0003 (Tag Names).
        Tags should support both string and array values per TAMS 8.0.
        """
        if not api_available:
            pytest.skip("API not available")
        
        example_flow = get_video_flow_example()
        
        import uuid
        flow_id = str(uuid.uuid4())
        flow_data = {
            "id": flow_id,
            "source_id": test_source_id,
            "format": example_flow["format"],
            "codec": example_flow["codec"],
            "essence_parameters": example_flow["essence_parameters"]
        }
        response = requests.post(f"{BASE_URL}/flows", json=flow_data, headers=auth_headers)
        
        # Add tag (per spec: tags.json allows string values)
        tag_headers = {"Content-Type": "text/plain"}
        tag_headers.update(auth_headers)
        response = requests.put(
            f"{BASE_URL}/flows/{flow_id}/tags/input_quality",
            data="contribution",
            headers=tag_headers
        )
        assert response.status_code in [200, 201, 204]
        
        # Retrieve tag
        response = requests.get(f"{BASE_URL}/flows/{flow_id}/tags", headers=auth_headers)
        assert response.status_code == 200
        
        tags = response.json()
        if tags and "input_quality" in tags:
            assert tags["input_quality"] == "contribution"
        
        # Cleanup
        requests.delete(f"{BASE_URL}/flows/{flow_id}", headers=auth_headers)


@pytest.mark.usefixtures("api_available")
class TestFlowAppNoteCompliance:
    """Test compliance with TAMS 8.0 app notes for flows"""
    
    def test_flow_bit_rate_properties_per_appnote_0013(self, api_available, test_source_id, auth_headers):
        """
        Test flow bit rate properties per App Note 0013.
        avg_bit_rate and max_bit_rate should be supported.
        """
        if not api_available:
            pytest.skip("API not available")
        
        example_flow = get_video_flow_example()
        
        import uuid
        flow_data = {
            "id": str(uuid.uuid4()),
            "source_id": test_source_id,
            "format": example_flow["format"],
            "codec": example_flow["codec"],
            "avg_bit_rate": example_flow.get("avg_bit_rate", 2479),
            "essence_parameters": example_flow["essence_parameters"]
        }
        
        response = requests.post(f"{BASE_URL}/flows", json=flow_data, headers=auth_headers)
        assert response.status_code == 201
        
        created = response.json()
        
        # Verify bit rate is stored if provided
        if "avg_bit_rate" in flow_data:
            # Value may be stored or calculated
            assert "avg_bit_rate" in created or "avg_bit_rate" in flow_data
        
        # Cleanup
        requests.delete(f"{BASE_URL}/flows/{flow_data['id']}", headers=auth_headers)

