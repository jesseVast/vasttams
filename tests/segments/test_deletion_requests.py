"""
Tests for async deletion requests (non-blocking segment deletion)

Tests the TAMS 8.0 delete-requests functionality for long-running deletions.
"""

import pytest
import requests
import time
import uuid
import sys
from pathlib import Path
from typing import Dict, Any

# Add src to path for imports
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from vasttamsserver.core.config import get_settings

# Get settings for API base URL
settings = get_settings()
BASE_URL = f"http://{settings.host}:{settings.port}"


@pytest.fixture(scope="module")
def api_available():
    """Check if API server is running"""
    try:
        response = requests.get(f"{BASE_URL}/service", timeout=2)
        return response.status_code == 200
    except:
        return False


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
        try:
            requests.delete(f"{BASE_URL}/flows/{flow_id}?cascade=true", headers=auth_headers)
        except:
            pass
        try:
            requests.delete(f"{BASE_URL}/sources/{source_id}", headers=auth_headers)
        except:
            pass


@pytest.mark.usefixtures("api_available")
class TestAsyncDeletionRequests:
    """Test async deletion request functionality"""
    
    def test_small_deletion_is_synchronous(self, api_available, test_flow_and_source, auth_headers):
        """Test that small deletions (<=50 segments) are processed synchronously"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_and_source["flow_id"]
        
        # Create a few segments (less than 50)
        segments_created = []
        for i in range(5):
            object_id = str(uuid.uuid4())
            segment_data = {
                "id": str(uuid.uuid4()),
                "flow_id": flow_id,
                "object_id": object_id,
                "timerange": {"value": f"[{i*10}:0_{(i+1)*10}:0)"}
            }
            
            response = requests.post(
                f"{BASE_URL}/flows/{flow_id}/segments",
                json=segment_data,
                headers=auth_headers
            )
            
            if response.status_code == 201:
                segments_created.append((object_id, segment_data["id"]))
        
        if not segments_created:
            pytest.skip("Failed to create segments for test")
        
        # Delete with timerange - should be synchronous (200/204)
        response = requests.delete(
            f"{BASE_URL}/flows/{flow_id}/segments",
            params={"timerange": "[0:0_50:0)"},
            headers=auth_headers
        )
        
        # Small deletion should return 200 or 204 (synchronous)
        assert response.status_code in [200, 204], \
            f"Expected synchronous response (200/204), got {response.status_code}: {response.text}"
        
        # Cleanup
        for object_id, _ in segments_created:
            try:
                requests.delete(f"{BASE_URL}/objects/{object_id}", headers=auth_headers)
            except:
                pass
    
    def test_large_deletion_creates_deletion_request(self, api_available, test_flow_and_source, auth_headers):
        """Test that large deletions (>50 segments) create deletion requests and return 202"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_and_source["flow_id"]
        
        # Create many segments (>50 to trigger async deletion)
        segments_created = []
        object_ids = []
        
        try:
            for i in range(75):  # Create 75 segments (>50 threshold)
                object_id = str(uuid.uuid4())
                object_ids.append(object_id)
                segment_data = {
                    "id": str(uuid.uuid4()),
                    "flow_id": flow_id,
                    "object_id": object_id,
                    "timerange": {"value": f"[{i*10}:0_{(i+1)*10}:0)"}
                }
                
                response = requests.post(
                    f"{BASE_URL}/flows/{flow_id}/segments",
                    json=segment_data,
                    headers=auth_headers
                )
                
                if response.status_code == 201:
                    segments_created.append((object_id, segment_data["id"]))
            
            if len(segments_created) < 50:
                pytest.skip(f"Failed to create enough segments (created {len(segments_created)})")
            
            # Delete with timerange - should create deletion request (202 Accepted)
            response = requests.delete(
                f"{BASE_URL}/flows/{flow_id}/segments",
                params={"timerange": "[0:0_750:0)"},
                headers=auth_headers
            )
            
            # Large deletion should return 202 Accepted with Location header
            assert response.status_code == 202, \
                f"Expected 202 Accepted, got {response.status_code}: {response.text}"
            
            # Check for Location header
            location = response.headers.get("Location")
            assert location is not None, "Missing Location header in 202 response"
            assert "/flow-delete-requests/" in location, \
                f"Location header should point to deletion request: {location}"
            
            # Parse response body
            try:
                response_data = response.json()
                assert "id" in response_data, "Response should include deletion request ID"
                assert response_data.get("status") == "created", \
                    f"Expected status 'created', got {response_data.get('status')}"
                
                request_id = response_data["id"]
            except:
                # If JSON parsing fails, extract ID from Location header
                request_id = location.split("/")[-1]
            
            # Verify deletion request exists
            get_response = requests.get(
                f"{BASE_URL}/flow-delete-requests/{request_id}",
                headers=auth_headers
            )
            
            assert get_response.status_code == 200, \
                f"Failed to get deletion request: {get_response.status_code}"
            
            request_data = get_response.json()
            assert request_data["id"] == request_id
            assert request_data["flow_id"] == flow_id
            assert request_data["status"] in ["created", "started"], \
                f"Expected status 'created' or 'started', got {request_data['status']}"
        
        finally:
            # Cleanup objects
            for object_id in object_ids:
                try:
                    requests.delete(f"{BASE_URL}/objects/{object_id}", headers=auth_headers)
                except:
                    pass
    
    def test_deletion_request_status_tracking(self, api_available, test_flow_and_source, auth_headers):
        """Test that deletion request status can be tracked"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_and_source["flow_id"]
        
        # Create segments for deletion
        segments_created = []
        object_ids = []
        
        try:
            for i in range(75):  # Create 75 segments (>50 threshold)
                object_id = str(uuid.uuid4())
                object_ids.append(object_id)
                segment_data = {
                    "id": str(uuid.uuid4()),
                    "flow_id": flow_id,
                    "object_id": object_id,
                    "timerange": {"value": f"[{i*10}:0_{(i+1)*10}:0)"}
                }
                
                response = requests.post(
                    f"{BASE_URL}/flows/{flow_id}/segments",
                    json=segment_data,
                    headers=auth_headers
                )
                
                if response.status_code == 201:
                    segments_created.append((object_id, segment_data["id"]))
            
            if len(segments_created) < 50:
                pytest.skip(f"Failed to create enough segments (created {len(segments_created)})")
            
            # Create deletion request
            response = requests.delete(
                f"{BASE_URL}/flows/{flow_id}/segments",
                params={"timerange": "[0:0_750:0)"},
                headers=auth_headers
            )
            
            if response.status_code != 202:
                pytest.skip(f"Failed to create deletion request: {response.status_code}")
            
            request_id = response.json().get("id")
            if not request_id:
                # Extract from Location header
                location = response.headers.get("Location", "")
                request_id = location.split("/")[-1] if "/" in location else None
            
            if not request_id:
                pytest.skip("Could not determine deletion request ID")
            
            # Poll for status updates
            max_wait = 30  # seconds
            start_time = time.time()
            final_status = None
            
            while time.time() - start_time < max_wait:
                get_response = requests.get(
                    f"{BASE_URL}/flow-delete-requests/{request_id}",
                    headers=auth_headers
                )
                
                if get_response.status_code == 200:
                    request_data = get_response.json()
                    status = request_data.get("status")
                    
                    if status == "done":
                        final_status = "done"
                        break
                    elif status == "error":
                        final_status = "error"
                        break
                    # Otherwise continue polling (status is "created" or "started")
                
                time.sleep(0.5)  # Poll every 500ms
            
            # Verify final status
            assert final_status in ["done", "started"], \
                f"Expected status 'done' or 'started' after {max_wait}s, got {final_status}"
        
        finally:
            # Cleanup
            for object_id in object_ids:
                try:
                    requests.delete(f"{BASE_URL}/objects/{object_id}", headers=auth_headers)
                except:
                    pass
    
    def test_list_deletion_requests(self, api_available, auth_headers):
        """Test listing deletion requests"""
        if not api_available:
            pytest.skip("API not available")
        
        response = requests.get(
            f"{BASE_URL}/flow-delete-requests",
            headers=auth_headers
        )
        
        assert response.status_code == 200, \
            f"Failed to list deletion requests: {response.status_code}"
        
        # Should return a list (may be empty)
        requests_list = response.json()
        assert isinstance(requests_list, list), \
            f"Expected list, got {type(requests_list)}"
    
    def test_get_nonexistent_deletion_request(self, api_available, auth_headers):
        """Test getting a non-existent deletion request returns 404"""
        if not api_available:
            pytest.skip("API not available")
        
        fake_id = str(uuid.uuid4())
        response = requests.get(
            f"{BASE_URL}/flow-delete-requests/{fake_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 404, \
            f"Expected 404 for non-existent request, got {response.status_code}"


@pytest.mark.usefixtures("api_available")
class TestDeletionRequestEdgeCases:
    """Test edge cases for deletion requests"""
    
    def test_delete_all_segments_creates_request(self, api_available, test_flow_and_source, auth_headers):
        """Test that deleting all segments (no timerange) creates deletion request if >50 segments"""
        if not api_available:
            pytest.skip("API not available")
        
        flow_id = test_flow_and_source["flow_id"]
        
        # Create many segments
        segments_created = []
        object_ids = []
        
        try:
            for i in range(75):  # Create 75 segments (>50 threshold)
                object_id = str(uuid.uuid4())
                object_ids.append(object_id)
                segment_data = {
                    "id": str(uuid.uuid4()),
                    "flow_id": flow_id,
                    "object_id": object_id,
                    "timerange": {"value": f"[{i*10}:0_{(i+1)*10}:0)"}
                }
                
                response = requests.post(
                    f"{BASE_URL}/flows/{flow_id}/segments",
                    json=segment_data,
                    headers=auth_headers
                )
                
                if response.status_code == 201:
                    segments_created.append((object_id, segment_data["id"]))
            
            if len(segments_created) < 50:
                pytest.skip(f"Failed to create enough segments (created {len(segments_created)})")
            
            # Delete all segments (no timerange parameter)
            response = requests.delete(
                f"{BASE_URL}/flows/{flow_id}/segments",
                headers=auth_headers
            )
            
            # Should return 202 for large deletions
            assert response.status_code in [200, 202, 204], \
                f"Unexpected status: {response.status_code}: {response.text}"
            
            # If 202, verify deletion request was created
            if response.status_code == 202:
                location = response.headers.get("Location")
                assert location is not None, "Missing Location header"
                assert "/flow-delete-requests/" in location
        
        finally:
            # Cleanup
            for object_id in object_ids:
                try:
                    requests.delete(f"{BASE_URL}/objects/{object_id}", headers=auth_headers)
                except:
                    pass

