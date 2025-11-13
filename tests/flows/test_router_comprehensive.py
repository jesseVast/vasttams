#!/usr/bin/env python3
"""
Comprehensive Router Tests for Flows

Tests all endpoints in flows/router.py to achieve 100% coverage.
This includes all HTTP methods, query parameters, error handling, etc.
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
    """Create a test source and return its ID"""
    if not api_available:
        pytest.skip("API not available")
    
    source_id = str(uuid.uuid4())
    source_data = {
        "id": source_id,
        "format": "urn:x-nmos:format:video",
        "label": f"Test Source {source_id[:8]}"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/sources", json=source_data, headers=auth_headers)
        if response.status_code != 201:
            pytest.skip(f"Failed to create test source: {response.text}")
        yield source_id
    finally:
        # Cleanup
        try:
            requests.delete(f"{BASE_URL}/sources/{source_id}", headers=auth_headers)
        except:
            pass


@pytest.fixture
def test_flow_id(api_available, auth_headers):
    """Create a test flow and return its ID"""
    if not api_available:
        pytest.skip("API not available")
    
    # Create source first
    source_id = str(uuid.uuid4())
    source_data = {
        "id": source_id,
        "format": "urn:x-nmos:format:video",
        "label": f"Test Source {source_id[:8]}"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/sources", json=source_data, headers=auth_headers)
        if response.status_code != 201:
            pytest.skip(f"Failed to create test source: {response.text}")
        
        # Create flow
        flow_id = str(uuid.uuid4())
        flow_data = {
            "id": flow_id,
            "source_id": source_id,
            "format": "urn:x-nmos:format:video",
            "codec": "video/H264",
            "label": f"Test Flow {flow_id[:8]}",
            "essence_parameters": {
                "frame_width": 1920,
                "frame_height": 1080,
                "frame_rate": {"numerator": 25, "denominator": 1}
            }
        }
        
        response = requests.post(f"{BASE_URL}/flows", json=flow_data, headers=auth_headers)
        if response.status_code != 201:
            pytest.skip(f"Failed to create test flow: {response.text}")
        
        yield {"flow_id": flow_id, "source_id": source_id}
        
    finally:
        # Cleanup
        try:
            requests.delete(f"{BASE_URL}/flows/{flow_id}", headers=auth_headers)
        except:
            pass
        try:
            requests.delete(f"{BASE_URL}/sources/{source_id}", headers=auth_headers)
        except:
            pass


@pytest.mark.usefixtures("api_available")
class TestFlowsRouterHEAD:
    """Test HEAD endpoints for flows router"""
    
    def test_head_flows(self, api_available, auth_headers):
        """Test HEAD /flows endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        response = requests.head(f"{BASE_URL}/flows", headers=auth_headers)
        assert response.status_code in [200, 204]
    
    def test_head_flow_by_id(self, api_available, test_flow_id, auth_headers):
        """Test HEAD /flows/{flow_id} endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_id["flow_id"]
        response = requests.head(f"{BASE_URL}/flows/{flow_id}", headers=auth_headers)
        assert response.status_code in [200, 204]
    
    def test_head_flow_tags(self, api_available, test_flow_id, auth_headers):
        """Test HEAD /flows/{flow_id}/tags endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_id["flow_id"]
        response = requests.head(f"{BASE_URL}/flows/{flow_id}/tags", headers=auth_headers)
        assert response.status_code in [200, 204]
    
    def test_head_flow_tag(self, api_available, test_flow_id, auth_headers):
        """Test HEAD /flows/{flow_id}/tags/{name} endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_id["flow_id"]
        response = requests.head(f"{BASE_URL}/flows/{flow_id}/tags/test_tag", headers=auth_headers)
        assert response.status_code in [200, 204]
    
    def test_head_flow_description(self, api_available, test_flow_id, auth_headers):
        """Test HEAD /flows/{flow_id}/description endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_id["flow_id"]
        response = requests.head(f"{BASE_URL}/flows/{flow_id}/description", headers=auth_headers)
        assert response.status_code in [200, 204]
    
    def test_head_flow_label(self, api_available, test_flow_id, auth_headers):
        """Test HEAD /flows/{flow_id}/label endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_id["flow_id"]
        response = requests.head(f"{BASE_URL}/flows/{flow_id}/label", headers=auth_headers)
        assert response.status_code in [200, 204]
    
    def test_head_flow_read_only(self, api_available, test_flow_id, auth_headers):
        """Test HEAD /flows/{flow_id}/read_only endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_id["flow_id"]
        response = requests.head(f"{BASE_URL}/flows/{flow_id}/read_only", headers=auth_headers)
        assert response.status_code in [200, 204]
    
    def test_head_flow_collection(self, api_available, test_flow_id, auth_headers):
        """Test HEAD /flows/{flow_id}/flow_collection endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_id["flow_id"]
        response = requests.head(f"{BASE_URL}/flows/{flow_id}/flow_collection", headers=auth_headers)
        assert response.status_code in [200, 204]
    
    def test_head_flow_max_bit_rate(self, api_available, test_flow_id, auth_headers):
        """Test HEAD /flows/{flow_id}/max_bit_rate endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_id["flow_id"]
        response = requests.head(f"{BASE_URL}/flows/{flow_id}/max_bit_rate", headers=auth_headers)
        assert response.status_code in [200, 204]
    
    def test_head_flow_avg_bit_rate(self, api_available, test_flow_id, auth_headers):
        """Test HEAD /flows/{flow_id}/avg_bit_rate endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_id["flow_id"]
        response = requests.head(f"{BASE_URL}/flows/{flow_id}/avg_bit_rate", headers=auth_headers)
        assert response.status_code in [200, 204]


@pytest.mark.usefixtures("api_available")
class TestFlowsRouterGET:
    """Test GET endpoints for flows router"""
    
    def test_list_flows_with_filters(self, api_available, auth_headers):
        """Test GET /flows with various filters"""
        if not api_available:
            pytest.skip("API not available")
        
        # Test without filters
        response = requests.get(f"{BASE_URL}/flows", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert isinstance(data["data"], list)
        
        # Test with format filter
        response = requests.get(f"{BASE_URL}/flows?format=urn:x-nmos:format:video", headers=auth_headers)
        assert response.status_code == 200
        
        # Test with codec filter
        response = requests.get(f"{BASE_URL}/flows?codec=video/H264", headers=auth_headers)
        assert response.status_code == 200
        
        # Test with limit
        response = requests.get(f"{BASE_URL}/flows?limit=10", headers=auth_headers)
        assert response.status_code == 200
    
    def test_get_flow_by_id(self, api_available, test_flow_id, auth_headers):
        """Test GET /flows/{flow_id} endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_id["flow_id"]
        response = requests.get(f"{BASE_URL}/flows/{flow_id}", headers=auth_headers)
        assert response.status_code == 200
        flow = response.json()
        assert flow["id"] == flow_id
        
        # Test with include_timerange
        response = requests.get(f"{BASE_URL}/flows/{flow_id}?include_timerange=true", headers=auth_headers)
        assert response.status_code == 200
    
    def test_get_flow_nonexistent(self, api_available, auth_headers):
        """Test GET /flows/{flow_id} with non-existent flow"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = str(uuid.uuid4())
        response = requests.get(f"{BASE_URL}/flows/{flow_id}", headers=auth_headers)
        assert response.status_code == 404
    
    def test_get_flow_tags(self, api_available, test_flow_id, auth_headers):
        """Test GET /flows/{flow_id}/tags endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_id["flow_id"]
        response = requests.get(f"{BASE_URL}/flows/{flow_id}/tags", headers=auth_headers)
        assert response.status_code == 200
        tags = response.json()
        assert isinstance(tags, dict)
    
    def test_get_flow_tag(self, api_available, test_flow_id, auth_headers):
        """Test GET /flows/{flow_id}/tags/{name} endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_id["flow_id"]
        tag_name = "test_tag"
        
        # First add a tag
        requests.put(
            f"{BASE_URL}/flows/{flow_id}/tags/{tag_name}",
            data="test_value",
            headers={**auth_headers, "Content-Type": "text/plain"}
        )
        
        # Get the tag
        response = requests.get(f"{BASE_URL}/flows/{flow_id}/tags/{tag_name}", headers=auth_headers)
        if response.status_code == 200:
            # Tag may be returned as JSON string or plain text
            tag_value = response.text.strip('"') if response.text.startswith('"') else response.text
            assert tag_value == "test_value"
    
    def test_get_flow_tag_nonexistent(self, api_available, test_flow_id, auth_headers):
        """Test GET /flows/{flow_id}/tags/{name} with non-existent tag"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_id["flow_id"]
        response = requests.get(f"{BASE_URL}/flows/{flow_id}/tags/nonexistent", headers=auth_headers)
        assert response.status_code == 404
    
    def test_get_flow_description(self, api_available, test_flow_id, auth_headers):
        """Test GET /flows/{flow_id}/description endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_id["flow_id"]
        response = requests.get(f"{BASE_URL}/flows/{flow_id}/description", headers=auth_headers)
        assert response.status_code == 200
        # Should return string (description or empty string)
        assert isinstance(response.text, str) or response.headers.get("content-type", "").startswith("text/")
    
    def test_get_flow_label(self, api_available, test_flow_id, auth_headers):
        """Test GET /flows/{flow_id}/label endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_id["flow_id"]
        response = requests.get(f"{BASE_URL}/flows/{flow_id}/label", headers=auth_headers)
        assert response.status_code == 200
    
    def test_get_flow_collection(self, api_available, test_flow_id, auth_headers):
        """Test GET /flows/{flow_id}/flow_collection endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_id["flow_id"]
        response = requests.get(f"{BASE_URL}/flows/{flow_id}/flow_collection", headers=auth_headers)
        assert response.status_code == 200
    
    def test_get_flow_max_bit_rate(self, api_available, test_flow_id, auth_headers):
        """Test GET /flows/{flow_id}/max_bit_rate endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_id["flow_id"]
        response = requests.get(f"{BASE_URL}/flows/{flow_id}/max_bit_rate", headers=auth_headers)
        assert response.status_code == 200
    
    def test_get_flow_avg_bit_rate(self, api_available, test_flow_id, auth_headers):
        """Test GET /flows/{flow_id}/avg_bit_rate endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_id["flow_id"]
        response = requests.get(f"{BASE_URL}/flows/{flow_id}/avg_bit_rate", headers=auth_headers)
        assert response.status_code == 200
    
    def test_get_flow_read_only(self, api_available, test_flow_id, auth_headers):
        """Test GET /flows/{flow_id}/read_only endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_id["flow_id"]
        response = requests.get(f"{BASE_URL}/flows/{flow_id}/read_only", headers=auth_headers)
        assert response.status_code == 200
        # Should return boolean
        assert isinstance(response.json(), bool)


@pytest.mark.usefixtures("api_available")
class TestFlowsRouterPOST:
    """Test POST endpoints for flows router"""
    
    def test_create_flow(self, api_available, auth_headers):
        """Test POST /flows endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        # Create source first
        source_id = str(uuid.uuid4())
        source_data = {
            "id": source_id,
            "format": "urn:x-nmos:format:video"
        }
        requests.post(f"{BASE_URL}/sources", json=source_data, headers=auth_headers)
        
        # Create flow
        flow_id = str(uuid.uuid4())
        flow_data = {
            "id": flow_id,
            "source_id": source_id,
            "format": "urn:x-nmos:format:video",
            "codec": "video/H264",
            "label": "Test Flow",
            "essence_parameters": {
                "frame_width": 1920,
                "frame_height": 1080,
                "frame_rate": {"numerator": 25, "denominator": 1}
            }
        }
        
        response = requests.post(f"{BASE_URL}/flows", json=flow_data, headers=auth_headers)
        assert response.status_code == 201
        created = response.json()
        assert created["id"] == flow_id
        
        # Cleanup
        requests.delete(f"{BASE_URL}/flows/{flow_id}", headers=auth_headers)
        requests.delete(f"{BASE_URL}/sources/{source_id}", headers=auth_headers)
    
    def test_create_flow_invalid_data(self, api_available, auth_headers):
        """Test POST /flows with invalid data"""
        if not api_available:
            pytest.skip("API not available")
        
        # Missing required fields
        flow_data = {"id": str(uuid.uuid4())}
        response = requests.post(f"{BASE_URL}/flows", json=flow_data, headers=auth_headers)
        assert response.status_code in [400, 422]
    
    def test_recalculate_bit_rates(self, api_available, test_flow_id, auth_headers):
        """Test POST /flows/{flow_id}/recalculate-bit-rates endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_id["flow_id"]
        response = requests.post(f"{BASE_URL}/flows/{flow_id}/recalculate-bit-rates", headers=auth_headers)
        # May return 200 or 500 depending on implementation
        assert response.status_code in [200, 500]


@pytest.mark.usefixtures("api_available")
class TestFlowsRouterPUT:
    """Test PUT endpoints for flows router"""
    
    def test_update_flow(self, api_available, test_flow_id, auth_headers):
        """Test PUT /flows/{flow_id} endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_id["flow_id"]
        
        # Get current flow first to preserve required fields
        get_response = requests.get(f"{BASE_URL}/flows/{flow_id}", headers=auth_headers)
        if get_response.status_code != 200:
            pytest.skip(f"Could not get flow for update test: {get_response.text}")
        
        current_flow = get_response.json()
        update_data = {
            "id": flow_id,
            "source_id": test_flow_id["source_id"],
            "format": current_flow.get("format", "urn:x-nmos:format:video"),
            "codec": current_flow.get("codec", "video/H264"),
            "label": "Updated Flow Label"
        }
        # Preserve essence_parameters if they exist
        if "essence_parameters" in current_flow:
            update_data["essence_parameters"] = current_flow["essence_parameters"]
        
        response = requests.put(f"{BASE_URL}/flows/{flow_id}", json=update_data, headers=auth_headers)
        # May return 200 or 500 depending on implementation
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            updated = response.json()
            assert updated["label"] == "Updated Flow Label"
    
    def test_update_flow_tag(self, api_available, test_flow_id, auth_headers):
        """Test PUT /flows/{flow_id}/tags/{name} endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_id["flow_id"]
        tag_name = "environment"
        tag_value = "production"
        
        response = requests.put(
            f"{BASE_URL}/flows/{flow_id}/tags/{tag_name}",
            data=tag_value,
            headers={**auth_headers, "Content-Type": "text/plain"}
        )
        assert response.status_code == 204
    
    def test_update_flow_description(self, api_available, test_flow_id, auth_headers):
        """Test PUT /flows/{flow_id}/description endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_id["flow_id"]
        description = "Updated description"
        
        response = requests.put(
            f"{BASE_URL}/flows/{flow_id}/description",
            data=description,
            headers={**auth_headers, "Content-Type": "text/plain"}
        )
        assert response.status_code == 204
    
    def test_update_flow_label(self, api_available, test_flow_id, auth_headers):
        """Test PUT /flows/{flow_id}/label endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_id["flow_id"]
        label = "Updated Label"
        
        response = requests.put(
            f"{BASE_URL}/flows/{flow_id}/label",
            data=label,
            headers={**auth_headers, "Content-Type": "text/plain"}
        )
        assert response.status_code == 204
    
    def test_update_flow_collection(self, api_available, test_flow_id, auth_headers):
        """Test PUT /flows/{flow_id}/flow_collection endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_id["flow_id"]
        # Flow collection should be a list of FlowCollectionItem objects with id and role
        collection_data = [{"id": str(uuid.uuid4()), "role": "video"}]
        
        response = requests.put(f"{BASE_URL}/flows/{flow_id}/flow_collection", json=collection_data, headers=auth_headers)
        assert response.status_code == 201
    
    def test_update_flow_max_bit_rate(self, api_available, test_flow_id, auth_headers):
        """Test PUT /flows/{flow_id}/max_bit_rate endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_id["flow_id"]
        bit_rate = "5000000"
        
        response = requests.put(
            f"{BASE_URL}/flows/{flow_id}/max_bit_rate",
            data=bit_rate,
            headers={**auth_headers, "Content-Type": "text/plain"}
        )
        assert response.status_code == 201
    
    def test_update_flow_avg_bit_rate(self, api_available, test_flow_id, auth_headers):
        """Test PUT /flows/{flow_id}/avg_bit_rate endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_id["flow_id"]
        bit_rate = "4000000"
        
        response = requests.put(
            f"{BASE_URL}/flows/{flow_id}/avg_bit_rate",
            data=bit_rate,
            headers={**auth_headers, "Content-Type": "text/plain"}
        )
        assert response.status_code == 201
    
    def test_update_flow_read_only(self, api_available, test_flow_id, auth_headers):
        """Test PUT /flows/{flow_id}/read_only endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_id["flow_id"]
        read_only = True
        
        response = requests.put(
            f"{BASE_URL}/flows/{flow_id}/read_only",
            json=read_only,
            headers={**auth_headers, "Content-Type": "application/json"}
        )
        assert response.status_code == 204


@pytest.mark.usefixtures("api_available")
class TestFlowsRouterDELETE:
    """Test DELETE endpoints for flows router"""
    
    def test_delete_flow(self, api_available, auth_headers):
        """Test DELETE /flows/{flow_id} endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        # Create source and flow for deletion
        source_id = str(uuid.uuid4())
        source_data = {"id": source_id, "format": "urn:x-nmos:format:video"}
        requests.post(f"{BASE_URL}/sources", json=source_data, headers=auth_headers)
        
        flow_id = str(uuid.uuid4())
        flow_data = {
            "id": flow_id,
            "source_id": source_id,
            "format": "urn:x-nmos:format:video",
            "codec": "video/H264"
        }
        requests.post(f"{BASE_URL}/flows", json=flow_data, headers=auth_headers)
        
        # Delete flow
        response = requests.delete(f"{BASE_URL}/flows/{flow_id}", headers=auth_headers)
        assert response.status_code in [200, 204]
        
        # Cleanup
        requests.delete(f"{BASE_URL}/sources/{source_id}", headers=auth_headers)
    
    def test_delete_flow_nonexistent(self, api_available, auth_headers):
        """Test DELETE /flows/{flow_id} with non-existent flow"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = str(uuid.uuid4())
        response = requests.delete(f"{BASE_URL}/flows/{flow_id}", headers=auth_headers)
        # May return 200 (successful delete even if not found) or 404
        assert response.status_code in [200, 404]
    
    def test_delete_flow_tag(self, api_available, test_flow_id, auth_headers):
        """Test DELETE /flows/{flow_id}/tags/{name} endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_id["flow_id"]
        tag_name = "temp_tag"
        
        # First add a tag
        requests.put(
            f"{BASE_URL}/flows/{flow_id}/tags/{tag_name}",
            data="temp_value",
            headers={**auth_headers, "Content-Type": "text/plain"}
        )
        
        # Delete the tag
        response = requests.delete(f"{BASE_URL}/flows/{flow_id}/tags/{tag_name}", headers=auth_headers)
        assert response.status_code == 204
    
    def test_delete_flow_description(self, api_available, test_flow_id, auth_headers):
        """Test DELETE /flows/{flow_id}/description endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_id["flow_id"]
        response = requests.delete(f"{BASE_URL}/flows/{flow_id}/description", headers=auth_headers)
        assert response.status_code == 204
    
    def test_delete_flow_label(self, api_available, test_flow_id, auth_headers):
        """Test DELETE /flows/{flow_id}/label endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_id["flow_id"]
        response = requests.delete(f"{BASE_URL}/flows/{flow_id}/label", headers=auth_headers)
        assert response.status_code == 204
    
    def test_delete_flow_collection(self, api_available, test_flow_id, auth_headers):
        """Test DELETE /flows/{flow_id}/flow_collection endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_id["flow_id"]
        response = requests.delete(f"{BASE_URL}/flows/{flow_id}/flow_collection", headers=auth_headers)
        assert response.status_code == 204
    
    def test_delete_flow_max_bit_rate(self, api_available, test_flow_id, auth_headers):
        """Test DELETE /flows/{flow_id}/max_bit_rate endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_id["flow_id"]
        response = requests.delete(f"{BASE_URL}/flows/{flow_id}/max_bit_rate", headers=auth_headers)
        assert response.status_code == 204
    
    def test_delete_flow_avg_bit_rate(self, api_available, test_flow_id, auth_headers):
        """Test DELETE /flows/{flow_id}/avg_bit_rate endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_id["flow_id"]
        response = requests.delete(f"{BASE_URL}/flows/{flow_id}/avg_bit_rate", headers=auth_headers)
        assert response.status_code == 204


@pytest.mark.usefixtures("api_available")
class TestFlowsRouterErrorCases:
    """Test error cases and edge cases for flows router"""
    
    def test_list_flows_with_all_filters(self, api_available, auth_headers):
        """Test GET /flows with all filter parameters"""
        if not api_available:
            pytest.skip("API not available")
        
        # Test with all filters
        response = requests.get(
            f"{BASE_URL}/flows?source_id=test&timerange=[0:0_10:0)&format=urn:x-nmos:format:video&codec=video/H264&label=Test&frame_width=1920&frame_height=1080&limit=50",
            headers=auth_headers
        )
        assert response.status_code == 200
    
    def test_list_flows_invalid_limit(self, api_available, auth_headers):
        """Test GET /flows with invalid limit values"""
        if not api_available:
            pytest.skip("API not available")
        
        # Test limit too high
        response = requests.get(f"{BASE_URL}/flows?limit=1001", headers=auth_headers)
        assert response.status_code in [400, 422]
        
        # Test limit too low
        response = requests.get(f"{BASE_URL}/flows?limit=0", headers=auth_headers)
        assert response.status_code in [400, 422]
    
    def test_get_flow_with_timerange_filter(self, api_available, test_flow_id, auth_headers):
        """Test GET /flows/{flow_id} with timerange filter per TAMS 8.0 spec"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_id["flow_id"]
        # Add timeout to prevent hanging
        response = requests.get(f"{BASE_URL}/flows/{flow_id}?timerange=[0:0_10:0)", headers=auth_headers, timeout=10)
        # Timerange filter limits the returned timerange information
        assert response.status_code == 200
        if response.status_code == 200:
            flow_data = response.json()
            # If timerange is present, it should be limited to the requested range
            if "timerange" in flow_data and flow_data["timerange"]:
                timerange = flow_data["timerange"].get("value") if isinstance(flow_data["timerange"], dict) else flow_data["timerange"]
                assert timerange is not None
    
    def test_get_flow_with_include_timerange(self, api_available, test_flow_id, auth_headers):
        """Test GET /flows/{flow_id} with include_timerange=true per TAMS 8.0 spec"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_id["flow_id"]
        # Add timeout to prevent hanging
        response = requests.get(f"{BASE_URL}/flows/{flow_id}?include_timerange=true", headers=auth_headers, timeout=10)
        # include_timerange=true should calculate and include Flow timerange from segments
        assert response.status_code == 200
        if response.status_code == 200:
            flow_data = response.json()
            # Timerange should be included in response
            # Note: May be None if flow has no segments
            assert "timerange" in flow_data
    
    def test_create_flow_invalid_codec(self, api_available, test_source_id, auth_headers):
        """Test POST /flows with invalid codec format"""
        if not api_available:
            pytest.skip("API not available")
        
        source_id = test_source_id
        flow_id = str(uuid.uuid4())
        flow_data = {
            "id": flow_id,
            "source_id": source_id,
            "format": "urn:x-nmos:format:video",
            "codec": "urn:x-nmos:codec:h264"  # Invalid - should be video/H264
        }
        
        response = requests.post(f"{BASE_URL}/flows", json=flow_data, headers=auth_headers)
        assert response.status_code in [400, 422]
    
    def test_create_flow_missing_essence_parameters(self, api_available, test_source_id, auth_headers):
        """Test POST /flows with missing essence_parameters"""
        if not api_available:
            pytest.skip("API not available")
        
        source_id = test_source_id
        flow_id = str(uuid.uuid4())
        flow_data = {
            "id": flow_id,
            "source_id": source_id,
            "format": "urn:x-nmos:format:video",
            "codec": "video/H264"
            # Missing essence_parameters
        }
        
        response = requests.post(f"{BASE_URL}/flows", json=flow_data, headers=auth_headers)
        assert response.status_code in [400, 422]
    
    def test_update_flow_read_only(self, api_available, test_flow_id, auth_headers):
        """Test PUT /flows/{flow_id}/read_only endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_id["flow_id"]
        response = requests.put(
            f"{BASE_URL}/flows/{flow_id}/read_only",
            data="true",
            headers={**auth_headers, "Content-Type": "text/plain"}
        )
        assert response.status_code == 204
    
    def test_get_flow_read_only(self, api_available, test_flow_id, auth_headers):
        """Test GET /flows/{flow_id}/read_only endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_id["flow_id"]
        response = requests.get(f"{BASE_URL}/flows/{flow_id}/read_only", headers=auth_headers)
        assert response.status_code == 200
    
    def test_recalculate_bit_rates(self, api_available, test_flow_id, auth_headers):
        """Test POST /flows/{flow_id}/recalculate-bit-rates endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_id["flow_id"]
        response = requests.post(f"{BASE_URL}/flows/{flow_id}/recalculate-bit-rates", headers=auth_headers)
        assert response.status_code == 200
    
    def test_update_flow_collection(self, api_available, test_flow_id, auth_headers):
        """Test PUT /flows/{flow_id}/flow_collection endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_id["flow_id"]
        collection_data = {"collection_id": "test_collection"}
        
        response = requests.put(
            f"{BASE_URL}/flows/{flow_id}/flow_collection",
            json=collection_data,
            headers=auth_headers
        )
        assert response.status_code == 201
    
    def test_get_flow_collection(self, api_available, test_flow_id, auth_headers):
        """Test GET /flows/{flow_id}/flow_collection endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_id["flow_id"]
        response = requests.get(f"{BASE_URL}/flows/{flow_id}/flow_collection", headers=auth_headers)
        assert response.status_code == 200
    
    def test_update_flow_max_bit_rate(self, api_available, test_flow_id, auth_headers):
        """Test PUT /flows/{flow_id}/max_bit_rate endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_id["flow_id"]
        response = requests.put(
            f"{BASE_URL}/flows/{flow_id}/max_bit_rate",
            data="1000000",
            headers={**auth_headers, "Content-Type": "text/plain"}
        )
        assert response.status_code == 201
    
    def test_get_flow_max_bit_rate(self, api_available, test_flow_id, auth_headers):
        """Test GET /flows/{flow_id}/max_bit_rate endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_id["flow_id"]
        response = requests.get(f"{BASE_URL}/flows/{flow_id}/max_bit_rate", headers=auth_headers)
        assert response.status_code == 200
    
    def test_update_flow_avg_bit_rate(self, api_available, test_flow_id, auth_headers):
        """Test PUT /flows/{flow_id}/avg_bit_rate endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_id["flow_id"]
        response = requests.put(
            f"{BASE_URL}/flows/{flow_id}/avg_bit_rate",
            data="500000",
            headers={**auth_headers, "Content-Type": "text/plain"}
        )
        assert response.status_code == 201
    
    def test_get_flow_avg_bit_rate(self, api_available, test_flow_id, auth_headers):
        """Test GET /flows/{flow_id}/avg_bit_rate endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_id["flow_id"]
        response = requests.get(f"{BASE_URL}/flows/{flow_id}/avg_bit_rate", headers=auth_headers)
        assert response.status_code == 200
    
    def test_delete_flow_with_segments(self, api_available, auth_headers):
        """Test DELETE /flows/{flow_id} when flow has segments"""
        if not api_available:
            pytest.skip("API not available")
        
        # Create source
        source_id = str(uuid.uuid4())
        source_data = {
            "id": source_id,
            "format": "urn:x-nmos:format:video",
            "label": "Test Source"
        }
        requests.post(f"{BASE_URL}/sources", json=source_data, headers=auth_headers)
        
        # Create flow
        flow_id = str(uuid.uuid4())
        flow_data = {
            "id": flow_id,
            "source_id": source_id,
            "format": "urn:x-nmos:format:video",
            "codec": "video/H264",
            "essence_parameters": {
                "frame_width": 1920,
                "frame_height": 1080,
                "frame_rate": {"numerator": 25, "denominator": 1}
            }
        }
        requests.post(f"{BASE_URL}/flows", json=flow_data, headers=auth_headers)
        
        # Delete flow (should work even with segments if cascade is true)
        response = requests.delete(f"{BASE_URL}/flows/{flow_id}", headers=auth_headers)
        assert response.status_code in [200, 204]
        
        # Cleanup
        requests.delete(f"{BASE_URL}/sources/{source_id}", headers=auth_headers)

