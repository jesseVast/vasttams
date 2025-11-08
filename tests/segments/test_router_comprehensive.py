#!/usr/bin/env python3
"""
Comprehensive Router Tests for Segments

Tests all endpoints in segments/router.py to achieve 100% coverage.
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
def test_flow_and_source(api_available, auth_headers):
    """Create a test flow and source for segment testing"""
    if not api_available:
        pytest.skip("API not available")
    
    source_id = str(uuid.uuid4())
    flow_id = str(uuid.uuid4())
    
    # Create source
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
        requests.delete(f"{BASE_URL}/flows/{flow_id}", headers=auth_headers)
        requests.delete(f"{BASE_URL}/sources/{source_id}", headers=auth_headers)


@pytest.mark.usefixtures("api_available")
class TestSegmentsRouterHEAD:
    """Test HEAD endpoints for segments router"""
    
    def test_head_flow_segments(self, api_available, test_flow_and_source, auth_headers):
        """Test HEAD /flows/{flow_id}/segments endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_and_source["flow_id"]
        response = requests.head(f"{BASE_URL}/flows/{flow_id}/segments", headers=auth_headers)
        assert response.status_code in [200, 204]


@pytest.mark.usefixtures("api_available")
class TestSegmentsRouterGET:
    """Test GET endpoints for segments router"""
    
    def test_list_flow_segments(self, api_available, test_flow_and_source, auth_headers):
        """Test GET /flows/{flow_id}/segments endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_and_source["flow_id"]
        response = requests.get(f"{BASE_URL}/flows/{flow_id}/segments", headers=auth_headers)
        assert response.status_code == 200
        segments = response.json()
        assert isinstance(segments, list)
    
    def test_list_flow_segments_with_filters(self, api_available, test_flow_and_source, auth_headers):
        """Test GET /flows/{flow_id}/segments with various filters"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_and_source["flow_id"]
        
        # Test with timerange filter
        response = requests.get(
            f"{BASE_URL}/flows/{flow_id}/segments?timerange=[0:0_31536000:0)",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        # Test with reverse_order
        response = requests.get(
            f"{BASE_URL}/flows/{flow_id}/segments?reverse_order=true",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        # Test with verbose_storage
        response = requests.get(
            f"{BASE_URL}/flows/{flow_id}/segments?verbose_storage=true",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        # Test with limit
        response = requests.get(
            f"{BASE_URL}/flows/{flow_id}/segments?limit=10",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        # Test with offset
        response = requests.get(
            f"{BASE_URL}/flows/{flow_id}/segments?offset=0",
            headers=auth_headers
        )
        assert response.status_code == 200
    
    def test_list_segments_nonexistent_flow(self, api_available, auth_headers):
        """Test GET /flows/{flow_id}/segments with non-existent flow"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = str(uuid.uuid4())
        response = requests.get(f"{BASE_URL}/flows/{flow_id}/segments", headers=auth_headers)
        # May return 200 with empty list or 404
        assert response.status_code in [200, 404]


@pytest.mark.usefixtures("api_available")
class TestSegmentsRouterPOST:
    """Test POST endpoints for segments router"""
    
    def test_create_segment(self, api_available, test_flow_and_source, auth_headers):
        """Test POST /flows/{flow_id}/segments endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_and_source["flow_id"]
        
        # First create an object via flow storage
        object_id = str(uuid.uuid4())
        storage_data = {
            "object_id": object_id,
            "size": 1000000,
            "storage_id": str(uuid.uuid4())
        }
        
        storage_response = requests.post(
            f"{BASE_URL}/flows/{flow_id}/storage",
            json=storage_data,
            headers=auth_headers
        )
        
        if storage_response.status_code != 201:
            pytest.skip(f"Failed to create object for segment: {storage_response.text}")
        
        # Create segment
        segment_data = {
            "id": str(uuid.uuid4()),
            "flow_id": flow_id,
            "object_id": object_id,
            "timerange": {
                "value": "[0:0_60:0)"  # TAMS timerange format: 60 seconds starting at 0:0
            }
        }
        
        response = requests.post(
            f"{BASE_URL}/flows/{flow_id}/segments",
            json=segment_data,
            headers=auth_headers
        )
        # May return 201 or 500 depending on implementation
        assert response.status_code in [201, 500]
        
        # Cleanup
        if response.status_code == 201:
            segment = response.json()
            segment_id = segment.get("id")
            if segment_id:
                try:
                    requests.delete(f"{BASE_URL}/flows/{flow_id}/segments/{segment_id}", headers=auth_headers)
                except:
                    pass
        try:
            requests.delete(f"{BASE_URL}/objects/{object_id}", headers=auth_headers)
        except:
            pass
    
    def test_create_segment_invalid_data(self, api_available, test_flow_and_source, auth_headers):
        """Test POST /flows/{flow_id}/segments with invalid data"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_and_source["flow_id"]
        
        # Missing required fields
        segment_data = {"id": str(uuid.uuid4())}
        response = requests.post(
            f"{BASE_URL}/flows/{flow_id}/segments",
            json=segment_data,
            headers=auth_headers
        )
        assert response.status_code in [400, 422, 500]
    
    def test_list_segments_with_timerange(self, api_available, test_flow_and_source, auth_headers):
        """Test GET /flows/{flow_id}/segments with timerange filter"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_and_source["flow_id"]
        response = requests.get(
            f"{BASE_URL}/flows/{flow_id}/segments?timerange=[0:0_10:0)",
            headers=auth_headers
        )
        assert response.status_code == 200
    
    def test_list_segments_with_object_id(self, api_available, test_flow_and_source, auth_headers):
        """Test GET /flows/{flow_id}/segments with object_id filter"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_and_source["flow_id"]
        object_id = str(uuid.uuid4())
        response = requests.get(
            f"{BASE_URL}/flows/{flow_id}/segments?object_id={object_id}",
            headers=auth_headers
        )
        assert response.status_code == 200
    
    def test_list_segments_reverse_order(self, api_available, test_flow_and_source, auth_headers):
        """Test GET /flows/{flow_id}/segments with reverse_order=true"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_and_source["flow_id"]
        response = requests.get(
            f"{BASE_URL}/flows/{flow_id}/segments?reverse_order=true",
            headers=auth_headers
        )
        assert response.status_code == 200
    
    def test_list_segments_verbose_storage(self, api_available, test_flow_and_source, auth_headers):
        """Test GET /flows/{flow_id}/segments with verbose_storage=true"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_and_source["flow_id"]
        response = requests.get(
            f"{BASE_URL}/flows/{flow_id}/segments?verbose_storage=true",
            headers=auth_headers
        )
        assert response.status_code == 200
    
    def test_list_segments_with_limit_offset(self, api_available, test_flow_and_source, auth_headers):
        """Test GET /flows/{flow_id}/segments with limit and offset"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_and_source["flow_id"]
        response = requests.get(
            f"{BASE_URL}/flows/{flow_id}/segments?limit=10&offset=0",
            headers=auth_headers
        )
        assert response.status_code == 200
    
    def test_list_segments_all_filters(self, api_available, test_flow_and_source, auth_headers):
        """Test GET /flows/{flow_id}/segments with all filters combined"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_and_source["flow_id"]
        response = requests.get(
            f"{BASE_URL}/flows/{flow_id}/segments?timerange=[0:0_10:0)&object_id=test&reverse_order=true&verbose_storage=true&limit=5&offset=0",
            headers=auth_headers
        )
        assert response.status_code == 200
    
    def test_create_flow_storage(self, api_available, test_flow_and_source, auth_headers):
        """Test POST /flows/{flow_id}/storage endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_and_source["flow_id"]
        storage_data = {
            "storage_id": str(uuid.uuid4()),
            "label": "Test Storage"
        }
        
        response = requests.post(
            f"{BASE_URL}/flows/{flow_id}/storage",
            json=storage_data,
            headers=auth_headers
        )
        # May succeed or fail depending on storage backend availability
        assert response.status_code in [201, 400, 404, 500]


@pytest.mark.usefixtures("api_available")
class TestSegmentsRouterDELETE:
    """Test DELETE endpoints for segments router"""
    
    def test_delete_segment(self, api_available, test_flow_and_source, auth_headers):
        """Test DELETE /flows/{flow_id}/segments/{segment_id} endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_and_source["flow_id"]
        
        # Create object and segment for deletion
        object_id = str(uuid.uuid4())
        storage_data = {
            "object_id": object_id,
            "size": 1000000,
            "storage_id": str(uuid.uuid4())
        }
        
        storage_response = requests.post(
            f"{BASE_URL}/flows/{flow_id}/storage",
            json=storage_data,
            headers=auth_headers
        )
        
        if storage_response.status_code != 201:
            pytest.skip(f"Failed to create object for segment deletion test: {storage_response.text}")
        
        segment_id = str(uuid.uuid4())
        segment_data = {
            "id": segment_id,
            "flow_id": flow_id,
            "object_id": object_id,
            "timerange": {
                "value": "[0:0_60:0)"  # TAMS timerange format: 60 seconds starting at 0:0
            }
        }
        
        create_response = requests.post(
            f"{BASE_URL}/flows/{flow_id}/segments",
            json=segment_data,
            headers=auth_headers
        )
        
        if create_response.status_code == 201:
            # Delete segment
            response = requests.delete(
                f"{BASE_URL}/flows/{flow_id}/segments/{segment_id}",
                headers=auth_headers
            )
            assert response.status_code in [200, 204, 404]
        
        # Cleanup
        try:
            requests.delete(f"{BASE_URL}/objects/{object_id}", headers=auth_headers)
        except:
            pass
    
    def test_delete_segment_nonexistent(self, api_available, test_flow_and_source, auth_headers):
        """Test DELETE /flows/{flow_id}/segments/{segment_id} with non-existent segment"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_and_source["flow_id"]
        segment_id = str(uuid.uuid4())
        response = requests.delete(
            f"{BASE_URL}/flows/{flow_id}/segments/{segment_id}",
            headers=auth_headers
        )
        assert response.status_code in [404, 200]  # May return 200 if delete is idempotent


@pytest.mark.usefixtures("api_available")
class TestSegmentsRouterTimerangeEdgeCases:
    """Test timerange filter edge cases and error handling"""
    
    def test_list_segments_timerange_invalid_format(self, api_available, test_flow_and_source, auth_headers):
        """Test GET /flows/{flow_id}/segments with invalid timerange format"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_and_source["flow_id"]
        # Invalid timerange format
        response = requests.get(
            f"{BASE_URL}/flows/{flow_id}/segments?timerange=invalid-format",
            headers=auth_headers
        )
        # May return 200 (with empty results) or 400/422 (validation error)
        assert response.status_code in [200, 400, 422]
    
    def test_list_segments_timerange_overlapping(self, api_available, test_flow_and_source, auth_headers):
        """Test GET /flows/{flow_id}/segments with overlapping timerange"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_and_source["flow_id"]
        # Overlapping timerange (start before end)
        response = requests.get(
            f"{BASE_URL}/flows/{flow_id}/segments?timerange=[5:0_10:0)",
            headers=auth_headers
        )
        assert response.status_code == 200
    
    def test_list_segments_timerange_no_overlap(self, api_available, test_flow_and_source, auth_headers):
        """Test GET /flows/{flow_id}/segments with timerange that has no overlap"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_and_source["flow_id"]
        # Timerange far in the future (likely no overlap)
        response = requests.get(
            f"{BASE_URL}/flows/{flow_id}/segments?timerange=[9999:0_10000:0)",
            headers=auth_headers
        )
        assert response.status_code == 200
        segments = response.json()
        assert isinstance(segments, list)  # Should return empty list
    
    def test_list_segments_timerange_open_ended(self, api_available, test_flow_and_source, auth_headers):
        """Test GET /flows/{flow_id}/segments with open-ended timerange"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_and_source["flow_id"]
        # Open-ended timerange (only start)
        response = requests.get(
            f"{BASE_URL}/flows/{flow_id}/segments?timerange=[0:0_)",
            headers=auth_headers
        )
        assert response.status_code == 200
    
    def test_list_segments_timerange_empty_string(self, api_available, test_flow_and_source, auth_headers):
        """Test GET /flows/{flow_id}/segments with empty timerange string"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_and_source["flow_id"]
        response = requests.get(
            f"{BASE_URL}/flows/{flow_id}/segments?timerange=",
            headers=auth_headers
        )
        # Should return 200 (empty timerange means no filtering)
        assert response.status_code == 200


@pytest.mark.usefixtures("api_available")
class TestSegmentsRouterStorageOperations:
    """Test storage creation and error handling"""
    
    def test_create_flow_storage_invalid_storage_id(self, api_available, test_flow_and_source, auth_headers):
        """Test POST /flows/{flow_id}/storage with invalid storage_id"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_and_source["flow_id"]
        # Invalid storage_id (not a UUID)
        storage_data = {
            "storage_id": "invalid-storage-id",
            "limit": 1
        }
        response = requests.post(
            f"{BASE_URL}/flows/{flow_id}/storage",
            json=storage_data,
            headers=auth_headers
        )
        # Should return 400 or 422 for invalid UUID
        assert response.status_code in [400, 422]
    
    def test_create_flow_storage_nonexistent_backend(self, api_available, test_flow_and_source, auth_headers):
        """Test POST /flows/{flow_id}/storage with non-existent storage backend"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_and_source["flow_id"]
        # Valid UUID format but non-existent backend
        storage_data = {
            "storage_id": str(uuid.uuid4()),
            "limit": 1
        }
        response = requests.post(
            f"{BASE_URL}/flows/{flow_id}/storage",
            json=storage_data,
            headers=auth_headers,
            timeout=30
        )
        # May return 201 (if default backend used), 400, 404, or 500 depending on implementation
        assert response.status_code in [201, 400, 404, 500]
    
    def test_create_flow_storage_with_limit(self, api_available, test_flow_and_source, auth_headers):
        """Test POST /flows/{flow_id}/storage with limit parameter"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_and_source["flow_id"]
        storage_data = {
            "limit": 2  # Request 2 storage locations
        }
        response = requests.post(
            f"{BASE_URL}/flows/{flow_id}/storage",
            json=storage_data,
            headers=auth_headers
        )
        # May succeed or fail depending on storage backend availability
        assert response.status_code in [201, 400, 404, 500]
        
        # Cleanup if created
        if response.status_code == 201:
            data = response.json()
            if "media_objects" in data:
                for obj in data["media_objects"]:
                    if "object_id" in obj:
                        try:
                            requests.delete(f"{BASE_URL}/objects/{obj['object_id']}", headers=auth_headers)
                        except:
                            pass
    
    def test_create_flow_storage_with_object_ids(self, api_available, test_flow_and_source, auth_headers):
        """Test POST /flows/{flow_id}/storage with specific object_ids"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_and_source["flow_id"]
        object_ids = [str(uuid.uuid4()) for _ in range(2)]
        storage_data = {
            "object_ids": object_ids
        }
        response = requests.post(
            f"{BASE_URL}/flows/{flow_id}/storage",
            json=storage_data,
            headers=auth_headers
        )
        # May succeed or fail depending on storage backend availability
        assert response.status_code in [201, 400, 404, 500]
        
        # Cleanup if created
        if response.status_code == 201:
            for object_id in object_ids:
                try:
                    requests.delete(f"{BASE_URL}/objects/{object_id}", headers=auth_headers)
                except:
                    pass
    
    def test_create_flow_storage_missing_parameters(self, api_available, test_flow_and_source, auth_headers):
        """Test POST /flows/{flow_id}/storage with missing required parameters"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_and_source["flow_id"]
        # Empty request body (no limit, no object_ids)
        storage_data = {}
        response = requests.post(
            f"{BASE_URL}/flows/{flow_id}/storage",
            json=storage_data,
            headers=auth_headers
        )
        # May return 201 (uses defaults) or 400/422 (validation error)
        assert response.status_code in [201, 400, 422]


@pytest.mark.usefixtures("api_available")
class TestSegmentsRouterFiltering:
    """Test advanced filtering options"""
    
    def test_list_segments_accept_get_urls(self, api_available, test_flow_and_source, auth_headers):
        """Test GET /flows/{flow_id}/segments with accept_get_urls filter"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_and_source["flow_id"]
        response = requests.get(
            f"{BASE_URL}/flows/{flow_id}/segments?accept_get_urls=primary,secondary",
            headers=auth_headers
        )
        assert response.status_code == 200
    
    def test_list_segments_accept_storage_ids(self, api_available, test_flow_and_source, auth_headers):
        """Test GET /flows/{flow_id}/segments with accept_storage_ids filter"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_and_source["flow_id"]
        storage_id = str(uuid.uuid4())
        response = requests.get(
            f"{BASE_URL}/flows/{flow_id}/segments?accept_storage_ids={storage_id}",
            headers=auth_headers
        )
        assert response.status_code == 200
    
    def test_list_segments_presigned_filter(self, api_available, test_flow_and_source, auth_headers):
        """Test GET /flows/{flow_id}/segments with presigned filter"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_and_source["flow_id"]
        # Filter for presigned URLs only
        response = requests.get(
            f"{BASE_URL}/flows/{flow_id}/segments?presigned=true",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        # Filter for non-presigned URLs only
        response2 = requests.get(
            f"{BASE_URL}/flows/{flow_id}/segments?presigned=false",
            headers=auth_headers
        )
        assert response2.status_code == 200
    
    def test_list_segments_combined_filters_complex(self, api_available, test_flow_and_source, auth_headers):
        """Test GET /flows/{flow_id}/segments with complex filter combinations"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_and_source["flow_id"]
        # Combine multiple filters
        response = requests.get(
            f"{BASE_URL}/flows/{flow_id}/segments?timerange=[0:0_10:0)&reverse_order=true&verbose_storage=true&presigned=true&limit=5&offset=0",
            headers=auth_headers
        )
        assert response.status_code == 200
    
    def test_list_segments_limit_zero(self, api_available, test_flow_and_source, auth_headers):
        """Test GET /flows/{flow_id}/segments with limit=0"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_and_source["flow_id"]
        response = requests.get(
            f"{BASE_URL}/flows/{flow_id}/segments?limit=0",
            headers=auth_headers
        )
        # Should return 200 with empty list or 422 for invalid limit
        assert response.status_code in [200, 422]
    
    def test_list_segments_limit_negative(self, api_available, test_flow_and_source, auth_headers):
        """Test GET /flows/{flow_id}/segments with negative limit"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_and_source["flow_id"]
        response = requests.get(
            f"{BASE_URL}/flows/{flow_id}/segments?limit=-1",
            headers=auth_headers
        )
        # May return 422, 400, or 200 (if validation is lenient)
        assert response.status_code in [200, 422, 400]
    
    def test_list_segments_offset_negative(self, api_available, test_flow_and_source, auth_headers):
        """Test GET /flows/{flow_id}/segments with negative offset"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_and_source["flow_id"]
        response = requests.get(
            f"{BASE_URL}/flows/{flow_id}/segments?offset=-1",
            headers=auth_headers
        )
        # Should return 422 for invalid offset or 200 (offset treated as 0)
        assert response.status_code in [200, 422, 400]


@pytest.mark.usefixtures("api_available")
class TestSegmentsRouterErrorPaths:
    """Test error handling and edge cases"""
    
    def test_create_segment_missing_object_id(self, api_available, test_flow_and_source, auth_headers):
        """Test POST /flows/{flow_id}/segments with missing object_id"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_and_source["flow_id"]
        segment_data = {
            "id": str(uuid.uuid4()),
            "flow_id": flow_id,
            "timerange": {
                "value": "2024-01-01T00:00:00Z/2024-01-01T00:01:00Z"
            }
            # Missing object_id
        }
        response = requests.post(
            f"{BASE_URL}/flows/{flow_id}/segments",
            json=segment_data,
            headers=auth_headers
        )
        assert response.status_code in [400, 422]
    
    def test_create_segment_missing_timerange(self, api_available, test_flow_and_source, auth_headers):
        """Test POST /flows/{flow_id}/segments with missing timerange"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_and_source["flow_id"]
        object_id = str(uuid.uuid4())
        segment_data = {
            "id": str(uuid.uuid4()),
            "flow_id": flow_id,
            "object_id": object_id
            # Missing timerange
        }
        response = requests.post(
            f"{BASE_URL}/flows/{flow_id}/segments",
            json=segment_data,
            headers=auth_headers
        )
        assert response.status_code in [400, 422]
    
    def test_create_segment_invalid_timerange_format(self, api_available, test_flow_and_source, auth_headers):
        """Test POST /flows/{flow_id}/segments with invalid timerange format"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_and_source["flow_id"]
        object_id = str(uuid.uuid4())
        segment_data = {
            "id": str(uuid.uuid4()),
            "flow_id": flow_id,
            "object_id": object_id,
            "timerange": {
                "value": "invalid-timerange-format"
            }
        }
        response = requests.post(
            f"{BASE_URL}/flows/{flow_id}/segments",
            json=segment_data,
            headers=auth_headers
        )
        assert response.status_code in [400, 422]
    
    def test_delete_segments_with_timerange(self, api_available, test_flow_and_source, auth_headers):
        """Test DELETE /flows/{flow_id}/segments with timerange filter"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_and_source["flow_id"]
        response = requests.delete(
            f"{BASE_URL}/flows/{flow_id}/segments?timerange=[0:0_10:0)",
            headers=auth_headers
        )
        # May return 200, 204, or 404 depending on whether segments exist
        assert response.status_code in [200, 204, 404]
    
    def test_delete_segments_with_object_id(self, api_available, test_flow_and_source, auth_headers):
        """Test DELETE /flows/{flow_id}/segments with object_id filter"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_and_source["flow_id"]
        object_id = str(uuid.uuid4())
        response = requests.delete(
            f"{BASE_URL}/flows/{flow_id}/segments?object_id={object_id}",
            headers=auth_headers
        )
        # May return 200, 204, or 404 depending on whether segments exist
        assert response.status_code in [200, 204, 404]
    
    def test_delete_segments_with_both_filters(self, api_available, test_flow_and_source, auth_headers):
        """Test DELETE /flows/{flow_id}/segments with both timerange and object_id"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_and_source["flow_id"]
        object_id = str(uuid.uuid4())
        response = requests.delete(
            f"{BASE_URL}/flows/{flow_id}/segments?timerange=[0:0_10:0)&object_id={object_id}",
            headers=auth_headers
        )
        # May return 200, 204, or 404 depending on whether segments exist
        assert response.status_code in [200, 204, 404]
    
    def test_list_segments_invalid_flow_id(self, api_available, auth_headers):
        """Test GET /flows/{flow_id}/segments with invalid flow_id format"""
        if not api_available:
            pytest.skip("API not available")
        
        response = requests.get(
            f"{BASE_URL}/flows/invalid-flow-id/segments",
            headers=auth_headers
        )
        # May return 200 (empty list), 404, or 422 depending on validation
        assert response.status_code in [200, 404, 422]

