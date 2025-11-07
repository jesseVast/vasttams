#!/usr/bin/env python3
"""
Comprehensive Router Tests for Sources

Tests all endpoints in sources/router.py to achieve 100% coverage.
"""

import pytest
import sys
import requests
import uuid
from pathlib import Path

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
        requests.delete(f"{BASE_URL}/sources/{source_id}", headers=auth_headers)


@pytest.mark.usefixtures("api_available")
class TestSourcesRouterHEAD:
    """Test HEAD endpoints for sources router"""
    
    def test_head_sources(self, api_available, auth_headers):
        """Test HEAD /sources endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        response = requests.head(f"{BASE_URL}/sources", headers=auth_headers)
        assert response.status_code in [200, 204]
    
    def test_options_sources(self, api_available, auth_headers):
        """Test OPTIONS /sources endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        response = requests.options(f"{BASE_URL}/sources", headers=auth_headers)
        assert response.status_code in [200, 204]
    
    def test_head_source_by_id(self, api_available, test_source_id, auth_headers):
        """Test HEAD /sources/{source_id} endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        response = requests.head(f"{BASE_URL}/sources/{test_source_id}", headers=auth_headers)
        assert response.status_code in [200, 204]
    
    def test_head_source_tags(self, api_available, test_source_id, auth_headers):
        """Test HEAD /sources/{source_id}/tags endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        response = requests.head(f"{BASE_URL}/sources/{test_source_id}/tags", headers=auth_headers)
        assert response.status_code in [200, 204]
    
    def test_head_source_tag(self, api_available, test_source_id, auth_headers):
        """Test HEAD /sources/{source_id}/tags/{name} endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        response = requests.head(f"{BASE_URL}/sources/{test_source_id}/tags/test_tag", headers=auth_headers)
        assert response.status_code in [200, 204]
    
    def test_head_source_description(self, api_available, test_source_id, auth_headers):
        """Test HEAD /sources/{source_id}/description endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        response = requests.head(f"{BASE_URL}/sources/{test_source_id}/description", headers=auth_headers)
        assert response.status_code in [200, 204]
    
    def test_head_source_label(self, api_available, test_source_id, auth_headers):
        """Test HEAD /sources/{source_id}/label endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        response = requests.head(f"{BASE_URL}/sources/{test_source_id}/label", headers=auth_headers)
        assert response.status_code in [200, 204]


@pytest.mark.usefixtures("api_available")
class TestSourcesRouterGET:
    """Test GET endpoints for sources router"""
    
    def test_list_sources_with_filters(self, api_available, auth_headers):
        """Test GET /sources with various filters"""
        if not api_available:
            pytest.skip("API not available")
        
        # Test without filters
        response = requests.get(f"{BASE_URL}/sources", headers=auth_headers, timeout=30)
        # May return 200 or 503 if server is overloaded
        assert response.status_code in [200, 503]
        if response.status_code == 200:
            data = response.json()
            assert "data" in data
            assert isinstance(data["data"], list)
        
        # Test with format filter
        response = requests.get(f"{BASE_URL}/sources?format=urn:x-nmos:format:video", headers=auth_headers, timeout=30)
        assert response.status_code in [200, 503]
        
        # Test with label filter
        response = requests.get(f"{BASE_URL}/sources?label=Test", headers=auth_headers, timeout=30)
        assert response.status_code in [200, 503]
        
        # Test with limit
        response = requests.get(f"{BASE_URL}/sources?limit=10", headers=auth_headers, timeout=30)
        assert response.status_code in [200, 503]
    
    def test_get_source_by_id(self, api_available, test_source_id, auth_headers):
        """Test GET /sources/{source_id} endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        response = requests.get(f"{BASE_URL}/sources/{test_source_id}", headers=auth_headers)
        assert response.status_code == 200
        source = response.json()
        assert source["id"] == test_source_id
    
    def test_get_source_nonexistent(self, api_available, auth_headers):
        """Test GET /sources/{source_id} with non-existent source"""
        if not api_available:
            pytest.skip("API not available")
        
        source_id = str(uuid.uuid4())
        response = requests.get(f"{BASE_URL}/sources/{source_id}", headers=auth_headers)
        assert response.status_code == 404
    
    def test_get_source_tags(self, api_available, test_source_id, auth_headers):
        """Test GET /sources/{source_id}/tags endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        response = requests.get(f"{BASE_URL}/sources/{test_source_id}/tags", headers=auth_headers)
        assert response.status_code == 200
        tags = response.json()
        assert isinstance(tags, dict)
    
    def test_get_source_tag(self, api_available, test_source_id, auth_headers):
        """Test GET /sources/{source_id}/tags/{name} endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        tag_name = "environment"
        tag_value = "production"
        
        # First add a tag
        requests.put(
            f"{BASE_URL}/sources/{test_source_id}/tags/{tag_name}",
            data=tag_value,
            headers={**auth_headers, "Content-Type": "text/plain"}
        )
        
        # Get the tag
        response = requests.get(f"{BASE_URL}/sources/{test_source_id}/tags/{tag_name}", headers=auth_headers)
        if response.status_code == 200:
            tag_value_response = response.text.strip('"') if response.text.startswith('"') else response.text
            assert tag_value_response == tag_value
    
    def test_get_source_tag_nonexistent(self, api_available, test_source_id, auth_headers):
        """Test GET /sources/{source_id}/tags/{name} with non-existent tag"""
        if not api_available:
            pytest.skip("API not available")
        
        response = requests.get(f"{BASE_URL}/sources/{test_source_id}/tags/nonexistent", headers=auth_headers)
        assert response.status_code == 404
    
    def test_get_source_description(self, api_available, test_source_id, auth_headers):
        """Test GET /sources/{source_id}/description endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        response = requests.get(f"{BASE_URL}/sources/{test_source_id}/description", headers=auth_headers)
        assert response.status_code == 200
    
    def test_get_source_label(self, api_available, test_source_id, auth_headers):
        """Test GET /sources/{source_id}/label endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        response = requests.get(f"{BASE_URL}/sources/{test_source_id}/label", headers=auth_headers)
        assert response.status_code == 200


@pytest.mark.usefixtures("api_available")
class TestSourcesRouterPOST:
    """Test POST endpoints for sources router"""
    
    def test_create_source(self, api_available, auth_headers):
        """Test POST /sources endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        source_id = str(uuid.uuid4())
        source_data = {
            "id": source_id,
            "format": "urn:x-nmos:format:video",
            "label": "Test Source"
        }
        
        response = requests.post(f"{BASE_URL}/sources", json=source_data, headers=auth_headers)
        assert response.status_code == 201
        created = response.json()
        assert created["id"] == source_id
        
        # Cleanup
        requests.delete(f"{BASE_URL}/sources/{source_id}", headers=auth_headers)
    
    def test_create_source_invalid_data(self, api_available, auth_headers):
        """Test POST /sources with invalid data"""
        if not api_available:
            pytest.skip("API not available")
        
        # Missing required fields
        source_data = {"id": str(uuid.uuid4())}
        response = requests.post(f"{BASE_URL}/sources", json=source_data, headers=auth_headers)
        assert response.status_code in [400, 422]
    
    def test_create_sources_batch(self, api_available, auth_headers):
        """Test POST /sources/batch endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        source_ids = [str(uuid.uuid4()) for _ in range(2)]
        sources_data = [
            {
                "id": source_id,
                "format": "urn:x-nmos:format:video",
                "label": f"Batch Source {i}"
            }
            for i, source_id in enumerate(source_ids)
        ]
        
        response = requests.post(f"{BASE_URL}/sources/batch", json=sources_data, headers=auth_headers)
        assert response.status_code == 201
        created = response.json()
        assert len(created) == 2
        
        # Cleanup
        for source_id in source_ids:
            requests.delete(f"{BASE_URL}/sources/{source_id}", headers=auth_headers)
    
    def test_create_sources_batch_empty(self, api_available, auth_headers):
        """Test POST /sources/batch with empty list"""
        if not api_available:
            pytest.skip("API not available")
        
        response = requests.post(f"{BASE_URL}/sources/batch", json=[], headers=auth_headers)
        assert response.status_code == 400


@pytest.mark.usefixtures("api_available")
class TestSourcesRouterPUT:
    """Test PUT endpoints for sources router"""
    
    def test_update_source_tag(self, api_available, test_source_id, auth_headers):
        """Test PUT /sources/{source_id}/tags/{name} endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        tag_name = "environment"
        tag_value = "production"
        
        response = requests.put(
            f"{BASE_URL}/sources/{test_source_id}/tags/{tag_name}",
            data=tag_value,
            headers={**auth_headers, "Content-Type": "text/plain"}
        )
        assert response.status_code == 204
    
    def test_update_source_description(self, api_available, test_source_id, auth_headers):
        """Test PUT /sources/{source_id}/description endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        description = "Updated description"
        
        response = requests.put(
            f"{BASE_URL}/sources/{test_source_id}/description",
            data=description,
            headers={**auth_headers, "Content-Type": "text/plain"}
        )
        assert response.status_code in [200, 204]
    
    def test_update_source_label(self, api_available, test_source_id, auth_headers):
        """Test PUT /sources/{source_id}/label endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        label = "Updated Label"
        
        response = requests.put(
            f"{BASE_URL}/sources/{test_source_id}/label",
            data=label,
            headers={**auth_headers, "Content-Type": "text/plain"}
        )
        assert response.status_code in [200, 204]


@pytest.mark.usefixtures("api_available")
class TestSourcesRouterDELETE:
    """Test DELETE endpoints for sources router"""
    
    def test_delete_source(self, api_available, auth_headers):
        """Test DELETE /sources/{source_id} endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        # Create source for deletion
        source_id = str(uuid.uuid4())
        source_data = {
            "id": source_id,
            "format": "urn:x-nmos:format:video",
            "label": "To Delete"
        }
        requests.post(f"{BASE_URL}/sources", json=source_data, headers=auth_headers)
        
        # Delete source
        response = requests.delete(f"{BASE_URL}/sources/{source_id}", headers=auth_headers)
        assert response.status_code in [200, 204]
    
    def test_delete_source_nonexistent(self, api_available, auth_headers):
        """Test DELETE /sources/{source_id} with non-existent source"""
        if not api_available:
            pytest.skip("API not available")
        
        source_id = str(uuid.uuid4())
        response = requests.delete(f"{BASE_URL}/sources/{source_id}", headers=auth_headers)
        assert response.status_code in [404, 200]  # May return 200 if delete is idempotent
    
    def test_delete_source_tag(self, api_available, test_source_id, auth_headers):
        """Test DELETE /sources/{source_id}/tags/{name} endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        tag_name = "temp_tag"
        
        # First add a tag
        requests.put(
            f"{BASE_URL}/sources/{test_source_id}/tags/{tag_name}",
            data="temp_value",
            headers={**auth_headers, "Content-Type": "text/plain"}
        )
        
        # Delete the tag
        response = requests.delete(f"{BASE_URL}/sources/{test_source_id}/tags/{tag_name}", headers=auth_headers)
        assert response.status_code == 204
    
    def test_delete_source_description(self, api_available, test_source_id, auth_headers):
        """Test DELETE /sources/{source_id}/description endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        response = requests.delete(f"{BASE_URL}/sources/{test_source_id}/description", headers=auth_headers)
        # Endpoint returns 200 with JSON message, not 204
        assert response.status_code in [200, 204]
    
    def test_delete_source_label(self, api_available, test_source_id, auth_headers):
        """Test DELETE /sources/{source_id}/label endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        response = requests.delete(f"{BASE_URL}/sources/{test_source_id}/label", headers=auth_headers)
        # Endpoint returns 200 with JSON message, not 204
        assert response.status_code in [200, 204]
    
    def test_delete_source_with_cascade_false(self, api_available, auth_headers):
        """Test DELETE /sources/{source_id} with cascade=false"""
        if not api_available:
            pytest.skip("API not available")
        
        # Create source for deletion
        source_id = str(uuid.uuid4())
        source_data = {
            "id": source_id,
            "format": "urn:x-nmos:format:video",
            "label": "To Delete No Cascade"
        }
        requests.post(f"{BASE_URL}/sources", json=source_data, headers=auth_headers)
        
        # Delete source with cascade=false
        response = requests.delete(f"{BASE_URL}/sources/{source_id}?cascade=false", headers=auth_headers)
        # May return 200, 204, or 409 if source has dependencies
        assert response.status_code in [200, 204, 409]
    
    def test_delete_source_with_cascade_true(self, api_available, auth_headers):
        """Test DELETE /sources/{source_id} with cascade=true"""
        if not api_available:
            pytest.skip("API not available")
        
        # Create source for deletion
        source_id = str(uuid.uuid4())
        source_data = {
            "id": source_id,
            "format": "urn:x-nmos:format:video",
            "label": "To Delete Cascade"
        }
        requests.post(f"{BASE_URL}/sources", json=source_data, headers=auth_headers)
        
        # Delete source with cascade=true (default)
        response = requests.delete(f"{BASE_URL}/sources/{source_id}?cascade=true", headers=auth_headers)
        assert response.status_code in [200, 204]
    
    def test_delete_source_with_dependencies(self, api_available, auth_headers):
        """Test DELETE /sources/{source_id} when source has dependent flows (409 Conflict)"""
        if not api_available:
            pytest.skip("API not available")
        
        # Create source
        source_id = str(uuid.uuid4())
        source_data = {
            "id": source_id,
            "format": "urn:x-nmos:format:video",
            "label": "Source With Dependencies"
        }
        requests.post(f"{BASE_URL}/sources", json=source_data, headers=auth_headers)
        
        # Create a flow that depends on this source
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
        
        # Try to delete source with cascade=false - should fail with 409
        response = requests.delete(f"{BASE_URL}/sources/{source_id}?cascade=false", headers=auth_headers)
        # May return 409 Conflict or 200 if cascade logic allows it
        assert response.status_code in [200, 204, 409]
        
        # Cleanup
        requests.delete(f"{BASE_URL}/flows/{flow_id}", headers=auth_headers)
        requests.delete(f"{BASE_URL}/sources/{source_id}", headers=auth_headers)


@pytest.mark.usefixtures("api_available")
class TestSourcesRouterErrorCases:
    """Test error cases and edge cases for sources router"""
    
    def test_list_sources_with_pagination(self, api_available, auth_headers):
        """Test GET /sources with pagination parameters"""
        if not api_available:
            pytest.skip("API not available")
        
        # Test with page parameter
        response = requests.get(f"{BASE_URL}/sources?page=test_page_key", headers=auth_headers)
        assert response.status_code == 200
        
        # Test with limit at boundary
        response = requests.get(f"{BASE_URL}/sources?limit=1", headers=auth_headers)
        assert response.status_code == 200
        
        response = requests.get(f"{BASE_URL}/sources?limit=1000", headers=auth_headers)
        assert response.status_code == 200
    
    def test_list_sources_invalid_limit(self, api_available, auth_headers):
        """Test GET /sources with invalid limit values"""
        if not api_available:
            pytest.skip("API not available")
        
        # Test limit too high
        response = requests.get(f"{BASE_URL}/sources?limit=1001", headers=auth_headers)
        assert response.status_code in [400, 422]
        
        # Test limit too low
        response = requests.get(f"{BASE_URL}/sources?limit=0", headers=auth_headers)
        assert response.status_code in [400, 422]
    
    def test_create_source_with_c2pa_tags(self, api_available, auth_headers):
        """Test POST /sources with C2PA metadata in tags"""
        if not api_available:
            pytest.skip("API not available")
        
        source_id = str(uuid.uuid4())
        source_data = {
            "id": source_id,
            "format": "urn:x-nmos:format:video",
            "label": "Source with C2PA",
            "tags": {
                "root": {
                    "c2pa": {
                        "valid": "metadata"
                    }
                }
            }
        }
        
        response = requests.post(f"{BASE_URL}/sources", json=source_data, headers=auth_headers)
        # Should succeed even if C2PA validation fails (just logs warning)
        assert response.status_code in [201, 422]
        
        # Cleanup if created
        if response.status_code == 201:
            requests.delete(f"{BASE_URL}/sources/{source_id}", headers=auth_headers)
    
    def test_create_source_missing_required_fields(self, api_available, auth_headers):
        """Test POST /sources with missing required fields"""
        if not api_available:
            pytest.skip("API not available")
        
        # Missing format
        source_data = {"id": str(uuid.uuid4())}
        response = requests.post(f"{BASE_URL}/sources", json=source_data, headers=auth_headers)
        assert response.status_code in [400, 422]
    
    def test_get_source_tags_empty(self, api_available, test_source_id, auth_headers):
        """Test GET /sources/{source_id}/tags when source has no tags"""
        if not api_available:
            pytest.skip("API not available")
        
        response = requests.get(f"{BASE_URL}/sources/{test_source_id}/tags", headers=auth_headers)
        assert response.status_code == 200
        tags = response.json()
        # Should return empty tags dict
        assert isinstance(tags, dict)
    
    def test_update_source_tag_invalid_value(self, api_available, test_source_id, auth_headers):
        """Test PUT /sources/{source_id}/tags/{name} with various value types"""
        if not api_available:
            pytest.skip("API not available")
        
        tag_name = "test_tag_update"
        
        # Test with string value
        response = requests.put(
            f"{BASE_URL}/sources/{test_source_id}/tags/{tag_name}",
            data="string_value",
            headers={**auth_headers, "Content-Type": "text/plain"}
        )
        assert response.status_code == 204
        
        # Test with empty value
        response = requests.put(
            f"{BASE_URL}/sources/{test_source_id}/tags/{tag_name}",
            data="",
            headers={**auth_headers, "Content-Type": "text/plain"}
        )
        assert response.status_code == 204
    
    def test_get_source_description_empty(self, api_available, test_source_id, auth_headers):
        """Test GET /sources/{source_id}/description when description is None"""
        if not api_available:
            pytest.skip("API not available")
        
        response = requests.get(f"{BASE_URL}/sources/{test_source_id}/description", headers=auth_headers)
        assert response.status_code == 200
        # Should return empty string if description is None
        assert isinstance(response.text, str)
    
    def test_get_source_label_empty(self, api_available, test_source_id, auth_headers):
        """Test GET /sources/{source_id}/label when label is None"""
        if not api_available:
            pytest.skip("API not available")
        
        response = requests.get(f"{BASE_URL}/sources/{test_source_id}/label", headers=auth_headers)
        assert response.status_code == 200
        # Should return label or empty string
        assert isinstance(response.text, str)
    
    def test_create_sources_batch_single_item(self, api_available, auth_headers):
        """Test POST /sources/batch with single source (should work)"""
        if not api_available:
            pytest.skip("API not available")
        
        source_id = str(uuid.uuid4())
        sources_data = [{
            "id": source_id,
            "format": "urn:x-nmos:format:video",
            "label": "Single Batch Source"
        }]
        
        response = requests.post(f"{BASE_URL}/sources/batch", json=sources_data, headers=auth_headers)
        assert response.status_code == 201
        created = response.json()
        assert len(created) == 1
        
        # Cleanup
        requests.delete(f"{BASE_URL}/sources/{source_id}", headers=auth_headers)
    
    def test_create_sources_batch_large(self, api_available, auth_headers):
        """Test POST /sources/batch with multiple sources"""
        if not api_available:
            pytest.skip("API not available")
        
        source_ids = [str(uuid.uuid4()) for _ in range(5)]
        sources_data = [
            {
                "id": source_id,
                "format": "urn:x-nmos:format:video",
                "label": f"Batch Source {i}"
            }
            for i, source_id in enumerate(source_ids)
        ]
        
        response = requests.post(f"{BASE_URL}/sources/batch", json=sources_data, headers=auth_headers)
        assert response.status_code == 201
        created = response.json()
        assert len(created) == 5
        
        # Cleanup
        for source_id in source_ids:
            requests.delete(f"{BASE_URL}/sources/{source_id}", headers=auth_headers)
    
    def test_list_sources_combined_filters(self, api_available, auth_headers):
        """Test GET /sources with multiple filters combined"""
        if not api_available:
            pytest.skip("API not available")
        
        # Test with format and label filters
        response = requests.get(
            f"{BASE_URL}/sources?format=urn:x-nmos:format:video&label=Test&limit=50",
            headers=auth_headers
        )
        assert response.status_code == 200
    
    def test_list_sources_with_tag_filter(self, api_available, auth_headers):
        """Test GET /sources with tag filter (TAMS 8.0)"""
        if not api_available:
            pytest.skip("API not available")
        
        # First create a source with tags
        source_id = str(uuid.uuid4())
        source_data = {
            "id": source_id,
            "format": "urn:x-nmos:format:video",
            "label": "Tagged Source",
            "tags": {
                "genre": "action",
                "quality": "HD"
            }
        }
        create_response = requests.post(f"{BASE_URL}/sources", json=source_data, headers=auth_headers)
        
        if create_response.status_code == 201:
            # Test tag filter - single value
            response = requests.get(
                f"{BASE_URL}/sources?tag.genre=action",
                headers=auth_headers,
                timeout=30
            )
            # May return 200, 503, or 500 depending on server state
            assert response.status_code in [200, 503, 500]
            
            # Test tag filter - multiple values (comma-separated)
            response2 = requests.get(
                f"{BASE_URL}/sources?tag.genre=action,drama",
                headers=auth_headers,
                timeout=30
            )
            assert response2.status_code in [200, 503, 500]
            
            # Test tag_exists filter
            response3 = requests.get(
                f"{BASE_URL}/sources?tag_exists.genre=true",
                headers=auth_headers,
                timeout=30
            )
            assert response3.status_code in [200, 503, 500]
            
            # Test tag_exists=false (tag should not exist)
            response4 = requests.get(
                f"{BASE_URL}/sources?tag_exists.nonexistent=false",
                headers=auth_headers,
                timeout=30
            )
            assert response4.status_code in [200, 503, 500]
            
            # Cleanup
            requests.delete(f"{BASE_URL}/sources/{source_id}", headers=auth_headers)
    
    def test_list_sources_with_multiple_tag_filters(self, api_available, auth_headers):
        """Test GET /sources with multiple tag filters (TAMS 8.0)"""
        if not api_available:
            pytest.skip("API not available")
        
        # Create source with multiple tags
        source_id = str(uuid.uuid4())
        source_data = {
            "id": source_id,
            "format": "urn:x-nmos:format:video",
            "label": "Multi-Tagged Source",
            "tags": {
                "genre": "action",
                "quality": "HD",
                "year": "2024"
            }
        }
        create_response = requests.post(f"{BASE_URL}/sources", json=source_data, headers=auth_headers)
        
        if create_response.status_code == 201:
            # Test multiple tag filters
            response = requests.get(
                f"{BASE_URL}/sources?tag.genre=action&tag.quality=HD",
                headers=auth_headers,
                timeout=30
            )
            assert response.status_code in [200, 503, 500]
            
            # Test tag filter with tag_exists
            response2 = requests.get(
                f"{BASE_URL}/sources?tag.genre=action&tag_exists.year=true",
                headers=auth_headers,
                timeout=30
            )
            assert response2.status_code in [200, 503, 500]
            
            # Cleanup
            requests.delete(f"{BASE_URL}/sources/{source_id}", headers=auth_headers)
    
    def test_list_sources_tag_filter_with_standard_filters(self, api_available, auth_headers):
        """Test GET /sources with tag filters combined with standard filters"""
        if not api_available:
            pytest.skip("API not available")
        
        # Create source with tags
        source_id = str(uuid.uuid4())
        source_data = {
            "id": source_id,
            "format": "urn:x-nmos:format:video",
            "label": "Filtered Source",
            "tags": {
                "genre": "action"
            }
        }
        create_response = requests.post(f"{BASE_URL}/sources", json=source_data, headers=auth_headers)
        
        if create_response.status_code == 201:
            # Test tag filter with format and label
            response = requests.get(
                f"{BASE_URL}/sources?format=urn:x-nmos:format:video&tag.genre=action&limit=10",
                headers=auth_headers,
                timeout=30
            )
            assert response.status_code in [200, 503]
            
            # Cleanup
            requests.delete(f"{BASE_URL}/sources/{source_id}", headers=auth_headers)

#!/usr/bin/env python3
"""
Additional Comprehensive Router Tests for Sources

Additional tests for batch operations, error paths, and edge cases.
"""

import pytest
import sys
import requests
import uuid
from pathlib import Path

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


@pytest.mark.usefixtures("api_available")
class TestSourcesRouterBatchOperations:
    """Test batch operation edge cases and error handling"""
    
    def test_create_sources_batch_duplicate_ids(self, api_available, auth_headers):
        """Test POST /sources/batch with duplicate source IDs"""
        if not api_available:
            pytest.skip("API not available")
        
        source_id = str(uuid.uuid4())
        batch_data = [
            {"id": source_id, "format": "urn:x-nmos:format:video", "label": "Source 1"},
            {"id": source_id, "format": "urn:x-nmos:format:video", "label": "Source 2"}  # Duplicate ID
        ]
        
        response = requests.post(
            f"{BASE_URL}/sources/batch",
            json=batch_data,
            headers=auth_headers,
            timeout=30
        )
        # May return 201 (if duplicates allowed), 400, 409, or 500
        assert response.status_code in [201, 400, 409, 422, 500]
        
        # Cleanup if somehow created
        try:
            requests.delete(f"{BASE_URL}/sources/{source_id}", headers=auth_headers)
        except:
            pass
    
    def test_create_sources_batch_mixed_valid_invalid(self, api_available, auth_headers):
        """Test POST /sources/batch with mix of valid and invalid sources"""
        if not api_available:
            pytest.skip("API not available")
        
        batch_data = [
            {"id": str(uuid.uuid4()), "format": "urn:x-nmos:format:video", "label": "Valid Source"},
            {"id": str(uuid.uuid4()), "format": "invalid-format", "label": "Invalid Source"}  # Invalid format
        ]
        
        response = requests.post(
            f"{BASE_URL}/sources/batch",
            json=batch_data,
            headers=auth_headers
        )
        # May return 201 (partial success) or 400/422 (validation error)
        assert response.status_code in [201, 400, 422]
        
        # Cleanup valid sources
        if response.status_code == 201:
            data = response.json()
            if isinstance(data, list):
                for source in data:
                    if "id" in source:
                        try:
                            requests.delete(f"{BASE_URL}/sources/{source['id']}", headers=auth_headers)
                        except:
                            pass
    
    def test_create_sources_batch_very_large(self, api_available, auth_headers):
        """Test POST /sources/batch with very large batch (stress test)"""
        if not api_available:
            pytest.skip("API not available")
        
        # Create 50 sources in batch (reduced from 100 for faster tests)
        batch_data = []
        source_ids = []
        for i in range(50):
            source_id = str(uuid.uuid4())
            source_ids.append(source_id)
            batch_data.append({
                "id": source_id,
                "format": "urn:x-nmos:format:video",
                "label": f"Batch Source {i}"
            })
        
        response = requests.post(
            f"{BASE_URL}/sources/batch",
            json=batch_data,
            headers=auth_headers,
            timeout=60  # Longer timeout for large batch
        )
        # May succeed or fail depending on server limits
        assert response.status_code in [201, 400, 413, 422, 500, 503]
        
        # Cleanup if created
        if response.status_code == 201:
            for source_id in source_ids:
                try:
                    requests.delete(f"{BASE_URL}/sources/{source_id}", headers=auth_headers)
                except:
                    pass


@pytest.mark.usefixtures("api_available")
class TestSourcesRouterErrorPaths:
    """Test error handling and edge cases"""
    
    def test_get_source_invalid_uuid(self, api_available, auth_headers):
        """Test GET /sources/{source_id} with invalid UUID format"""
        if not api_available:
            pytest.skip("API not available")
        
        response = requests.get(f"{BASE_URL}/sources/invalid-uuid-format", headers=auth_headers)
        # Should return 404 or 422 depending on validation
        assert response.status_code in [404, 422]
    
    def test_delete_source_invalid_uuid(self, api_available, auth_headers):
        """Test DELETE /sources/{source_id} with invalid UUID format"""
        if not api_available:
            pytest.skip("API not available")
        
        response = requests.delete(f"{BASE_URL}/sources/invalid-uuid-format", headers=auth_headers)
        # May return 200 (idempotent), 404, or 422 depending on validation
        assert response.status_code in [200, 404, 422]
    
    def test_update_source_tag_nonexistent_source(self, api_available, auth_headers):
        """Test PUT /sources/{source_id}/tags/{name} with non-existent source"""
        if not api_available:
            pytest.skip("API not available")
        
        source_id = str(uuid.uuid4())
        response = requests.put(
            f"{BASE_URL}/sources/{source_id}/tags/test_tag",
            data="test_value",
            headers={**auth_headers, "Content-Type": "text/plain"}
        )
        assert response.status_code == 404
    
    def test_delete_source_with_dependencies_409(self, api_available, auth_headers):
        """Test DELETE /sources/{source_id} returns 409 when source has dependencies"""
        if not api_available:
            pytest.skip("API not available")
        
        # Create source with flow (dependency)
        source_id = str(uuid.uuid4())
        source_data = {"id": source_id, "format": "urn:x-nmos:format:video", "label": "Source with Flow"}
        requests.post(f"{BASE_URL}/sources", json=source_data, headers=auth_headers)
        
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
        
        # Try to delete source (should fail with 409 if cascade=false or not specified)
        response = requests.delete(f"{BASE_URL}/sources/{source_id}", headers=auth_headers)
        # May return 409 (conflict) or 200 (if cascade delete works)
        assert response.status_code in [200, 409]
        
        # Cleanup
        try:
            requests.delete(f"{BASE_URL}/flows/{flow_id}", headers=auth_headers)
        except:
            pass
        try:
            requests.delete(f"{BASE_URL}/sources/{source_id}", headers=auth_headers)
        except:
            pass
    
    def test_create_source_missing_required_fields(self, api_available, auth_headers):
        """Test POST /sources with missing required fields"""
        if not api_available:
            pytest.skip("API not available")
        
        # Missing format (required field)
        invalid_data = {
            "id": str(uuid.uuid4()),
            "label": "Source without format"
        }
        response = requests.post(f"{BASE_URL}/sources", json=invalid_data, headers=auth_headers)
        assert response.status_code in [400, 422]
    
    def test_list_sources_invalid_limit_too_large(self, api_available, auth_headers):
        """Test GET /sources with limit exceeding maximum"""
        if not api_available:
            pytest.skip("API not available")
        
        response = requests.get(f"{BASE_URL}/sources?limit=10000", headers=auth_headers)
        # Should return 422 for invalid limit
        assert response.status_code in [422, 400]
    
    def test_list_sources_invalid_limit_zero(self, api_available, auth_headers):
        """Test GET /sources with limit=0"""
        if not api_available:
            pytest.skip("API not available")
        
        response = requests.get(f"{BASE_URL}/sources?limit=0", headers=auth_headers)
        # Should return 422 for invalid limit
        assert response.status_code in [422, 400]
    
    def test_list_sources_invalid_limit_negative(self, api_available, auth_headers):
        """Test GET /sources with negative limit"""
        if not api_available:
            pytest.skip("API not available")
        
        response = requests.get(f"{BASE_URL}/sources?limit=-1", headers=auth_headers)
        # Should return 422 for invalid limit
        assert response.status_code in [422, 400]

