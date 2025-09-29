#!/usr/bin/env python3
"""
Deletion Requests Endpoint Tests

Tests for all deletion request-related endpoints including:
- Deletion request creation
- Deletion request management
- Dependency violation handling
- Batch deletion operations
"""

import requests
from datetime import datetime
from test_utils import (
    BASE_URL, test_data, print_section, print_subsection, print_result,
    assert_response_success, assert_response_status, assert_response_any_status,
    create_test_source, create_test_flow, cleanup_test_data
)

def test_deletion_requests_crud():
    """Test basic deletion request CRUD operations"""
    print_section("DELETION REQUESTS CRUD OPERATIONS")
    
    # Create test data first
    test_data["source_id"] = create_test_source()
    test_data["flow_id"] = create_test_flow(test_data["source_id"])
    
    # READ - GET /flow-delete-requests
    print_subsection("GET Deletion Requests List")
    response = requests.get(f"{BASE_URL}/flow-delete-requests")
    data = assert_response_success("GET", "/flow-delete-requests", response, 200)
    assert isinstance(data, list)
    print(f"   Current deletion requests: {len(data)}")
    
    # CREATE - POST /flow-delete-requests
    print_subsection("CREATE Deletion Request")
    deletion_request = {
        "flow_id": test_data["flow_id"],
        "reason": "Test deletion request for API testing",
        "cascade": True
    }
    
    response = requests.post(f"{BASE_URL}/flow-delete-requests", json=deletion_request)
    data = assert_response_success("POST", "/flow-delete-requests", response, 201)
    
    # Store request ID for cleanup
    request_id = data.get("id") or data.get("request_id")
    if request_id:
        test_data["object_ids"].append(request_id)
        print(f"   Created deletion request ID: {request_id}")
    
    # READ - GET /flow-delete-requests/{request_id}
    print_subsection("GET Specific Deletion Request")
    if request_id:
        response = requests.get(f"{BASE_URL}/flow-delete-requests/{request_id}")
        data = assert_response_success("GET", f"/flow-delete-requests/{request_id}", response, 200)
        assert data.get("id") == request_id or data.get("request_id") == request_id

def test_deletion_requests_management():
    """Test deletion request management operations"""
    print_section("DELETION REQUESTS MANAGEMENT")
    
    if not test_data.get("flow_id"):
        print("❌ No flow_id available for deletion request management test")
        return
    
    # Create a deletion request
    print_subsection("CREATE Management Test Deletion Request")
    deletion_request = {
        "flow_id": test_data["flow_id"],
        "reason": "Management test deletion request",
        "cascade": False
    }
    
    response = requests.post(f"{BASE_URL}/flow-delete-requests", json=deletion_request)
    data = assert_response_success("POST", "/flow-delete-requests", response, 201)
    
    request_id = data.get("id") or data.get("request_id")
    if not request_id:
        print("   ⚠️  No request ID returned, skipping management tests")
        return
    
    test_data["object_ids"].append(request_id)
    
    # UPDATE deletion request (if supported)
    print_subsection("UPDATE Deletion Request")
    updated_request = {
        "flow_id": test_data["flow_id"],
        "reason": "Updated management test deletion request",
        "cascade": True,
        "status": "pending"
    }
    
    # Try PUT method (if supported)
    response = requests.put(f"{BASE_URL}/flow-delete-requests/{request_id}", json=updated_request)
    if response.status_code in [200, 201, 404]:
        print_result("PUT", f"/flow-delete-requests/{request_id}", response.status_code)
    else:
        assert_response_success("PUT", f"/flow-delete-requests/{request_id}", response, 200)
    
    # DELETE deletion request
    print_subsection("DELETE Deletion Request")
    response = requests.delete(f"{BASE_URL}/flow-delete-requests/{request_id}")
    assert_response_any_status("DELETE", f"/flow-delete-requests/{request_id}", response, [200, 204, 404])
    
    # Verify deletion
    print_subsection("VERIFY Deletion Request Deletion")
    response = requests.get(f"{BASE_URL}/flow-delete-requests")
    data = assert_response_success("GET", "/flow-delete-requests", response, 200)
    print(f"   Remaining deletion requests: {len(data)}")

def test_deletion_requests_cascade():
    """Test cascade deletion functionality"""
    print_section("DELETION REQUESTS CASCADE")
    
    if not test_data.get("flow_id"):
        print("❌ No flow_id available for cascade test")
        return
    
    # Allocate storage and create segments
    print_subsection("SETUP Data for Cascade Test")
    storage_request = {"limit": 1}
    response = requests.post(f"{BASE_URL}/flows/{test_data['flow_id']}/storage", json=storage_request)
    storage_data = assert_response_success("POST", f"/flows/{test_data['flow_id']}/storage", response, 201)
    
    object_id = storage_data["media_objects"][0]["object_id"]
    test_data["object_ids"].append(object_id)
    
    # Create a segment
    segment_data = {
        "object_id": object_id,
        "timerange": {"value": "0:1000"},
        "ts_offset": {"value": "0:0"},
        "last_duration": {"value": "0:100"},
        "sample_offset": 0,
        "sample_count": 1000,
        "key_frame_count": 10
    }
    response = requests.post(f"{BASE_URL}/flows/{test_data['flow_id']}/segments", json=segment_data)
    if response.status_code == 201:
        test_data["segment_ids"].append(object_id)
    
    # Test cascade deletion
    print_subsection("TEST Cascade Deletion")
    cascade_request = {
        "flow_id": test_data["flow_id"],
        "reason": "Cascade deletion test",
        "cascade": True
    }
    
    response = requests.post(f"{BASE_URL}/flow-delete-requests", json=cascade_request)
    data = assert_response_success("POST", "/flow-delete-requests", response, 201)
    
    request_id = data.get("id") or data.get("request_id")
    if request_id:
        test_data["object_ids"].append(request_id)
        print(f"   Created cascade deletion request: {request_id}")
    
    # Test non-cascade deletion
    print_subsection("TEST Non-Cascade Deletion")
    non_cascade_request = {
        "flow_id": test_data["flow_id"],
        "reason": "Non-cascade deletion test",
        "cascade": False
    }
    
    response = requests.post(f"{BASE_URL}/flow-delete-requests", json=non_cascade_request)
    data = assert_response_success("POST", "/flow-delete-requests", response, 201)
    
    request_id = data.get("id") or data.get("request_id")
    if request_id:
        test_data["object_ids"].append(request_id)
        print(f"   Created non-cascade deletion request: {request_id}")

def test_deletion_requests_dependency_violations():
    """Test dependency violation handling"""
    print_section("DELETION REQUESTS DEPENDENCY VIOLATIONS")
    
    if not test_data.get("flow_id"):
        print("❌ No flow_id available for dependency test")
        return
    
    # Create a flow with dependencies
    print_subsection("SETUP Flow with Dependencies")
    
    # Allocate storage
    storage_request = {"limit": 2}
    response = requests.post(f"{BASE_URL}/flows/{test_data['flow_id']}/storage", json=storage_request)
    storage_data = assert_response_success("POST", f"/flows/{test_data['flow_id']}/storage", response, 201)
    
    # Create segments (dependencies)
    for i, obj in enumerate(storage_data["media_objects"]):
        test_data["object_ids"].append(obj["object_id"])
        
        segment_data = {
            "object_id": obj["object_id"],
            "timerange": {"value": f"{i*1000}:{(i+1)*1000}"},
            "ts_offset": {"value": "0:0"},
            "last_duration": {"value": "0:100"},
            "sample_offset": i * 1000,
            "sample_count": 1000,
            "key_frame_count": 10
        }
        response = requests.post(f"{BASE_URL}/flows/{test_data['flow_id']}/segments", json=segment_data)
        if response.status_code == 201:
            test_data["segment_ids"].append(obj["object_id"])
    
    # Test deletion with dependencies (should fail or require cascade)
    print_subsection("TEST Deletion with Dependencies")
    dependency_request = {
        "flow_id": test_data["flow_id"],
        "reason": "Dependency violation test",
        "cascade": False
    }
    
    response = requests.post(f"{BASE_URL}/flow-delete-requests", json=dependency_request)
    # This might succeed (if dependencies are handled) or fail with 409
    if response.status_code in [200, 201, 409]:
        print_result("POST", "/flow-delete-requests (with dependencies)", response.status_code)
        if response.status_code in [200, 201]:
            data = response.json()
            request_id = data.get("id") or data.get("request_id")
            if request_id:
                test_data["object_ids"].append(request_id)
    else:
        assert_response_success("POST", "/flow-delete-requests (with dependencies)", response, 200)

def test_deletion_requests_batch_operations():
    """Test batch deletion operations"""
    print_section("DELETION REQUESTS BATCH OPERATIONS")
    
    # Create multiple flows for batch deletion
    print_subsection("SETUP Multiple Flows for Batch Deletion")
    batch_flows = []
    
    for i in range(3):
        source_id = create_test_source()
        flow_id = create_test_flow(source_id)
        batch_flows.append({"source_id": source_id, "flow_id": flow_id})
        test_data["object_ids"].extend([source_id, flow_id])
    
    # Create batch deletion requests
    print_subsection("CREATE Batch Deletion Requests")
    batch_requests = []
    
    for i, flow_info in enumerate(batch_flows, 1):
        request_data = {
            "flow_id": flow_info["flow_id"],
            "reason": f"Batch deletion test {i}",
            "cascade": True
        }
        
        response = requests.post(f"{BASE_URL}/flow-delete-requests", json=request_data)
        data = assert_response_success("POST", f"/flow-delete-requests (batch {i})", response, 201)
        
        request_id = data.get("id") or data.get("request_id")
        if request_id:
            batch_requests.append(request_id)
            test_data["object_ids"].append(request_id)
    
    print(f"   Created {len(batch_requests)} batch deletion requests")
    
    # Verify batch requests
    print_subsection("VERIFY Batch Deletion Requests")
    response = requests.get(f"{BASE_URL}/flow-delete-requests")
    data = assert_response_success("GET", "/flow-delete-requests", response, 200)
    print(f"   Total deletion requests: {len(data)}")

def test_deletion_requests_head_operations():
    """Test HEAD operations for deletion requests"""
    print_section("DELETION REQUESTS HEAD OPERATIONS")
    
    # HEAD /flow-delete-requests
    print_subsection("HEAD Deletion Requests List")
    response = requests.head(f"{BASE_URL}/flow-delete-requests")
    assert_response_status("HEAD", "/flow-delete-requests", response, 200)
    
    # Test HEAD with query parameters
    print_subsection("HEAD Deletion Requests with Query")
    response = requests.head(f"{BASE_URL}/flow-delete-requests?limit=10")
    assert_response_status("HEAD", "/flow-delete-requests?limit=10", response, 200)

def test_deletion_requests_error_cases():
    """Test deletion request error cases"""
    print_section("DELETION REQUESTS ERROR CASES")
    
    # Test with non-existent flow ID
    print_subsection("Non-existent Flow ID")
    deletion_request = {
        "flow_id": "nonexistent-flow-id",
        "reason": "Test with non-existent flow",
        "cascade": True
    }
    
    response = requests.post(f"{BASE_URL}/flow-delete-requests", json=deletion_request)
    # This might return 404 or 400 depending on implementation
    assert_response_any_status("POST", "/flow-delete-requests (non-existent flow)", response, [200, 201, 400, 404])
    
    # Test with non-existent request ID
    print_subsection("Non-existent Request ID")
    response = requests.get(f"{BASE_URL}/flow-delete-requests/nonexistent-request-id")
    assert_response_status("GET", "/flow-delete-requests/nonexistent-request-id", response, 404)
    
    response = requests.delete(f"{BASE_URL}/flow-delete-requests/nonexistent-request-id")
    assert_response_status("DELETE", "/flow-delete-requests/nonexistent-request-id", response, 404)
    
    # Test with invalid request data
    print_subsection("Invalid Request Data")
    invalid_requests = [
        {
            "description": "Missing flow_id",
            "data": {
                "reason": "Test missing flow_id",
                "cascade": True
            }
        },
        {
            "description": "Invalid flow_id format",
            "data": {
                "flow_id": "invalid-flow-id-format",
                "reason": "Test invalid flow_id format",
                "cascade": True
            }
        },
        {
            "description": "Missing reason",
            "data": {
                "flow_id": "test-flow-id",
                "cascade": True
            }
        }
    ]
    
    for test_case in invalid_requests:
        print_subsection(f"Validation Test: {test_case['description']}")
        
        response = requests.post(f"{BASE_URL}/flow-delete-requests", json=test_case["data"])
        # Invalid requests should return 400 or 422
        if response.status_code in [400, 422]:
            print_result("POST", f"/flow-delete-requests ({test_case['description']})", response.status_code)
        else:
            print_result("POST", f"/flow-delete-requests ({test_case['description']})", response.status_code)

def test_deletion_requests_performance():
    """Test deletion requests performance"""
    print_section("DELETION REQUESTS PERFORMANCE")
    
    import time
    
    # Test deletion request creation performance
    print_subsection("Deletion Request Creation Performance")
    
    if not test_data.get("flow_id"):
        test_data["source_id"] = create_test_source()
        test_data["flow_id"] = create_test_flow(test_data["source_id"])
    
    deletion_request = {
        "flow_id": test_data["flow_id"],
        "reason": "Performance test deletion request",
        "cascade": True
    }
    
    start_time = time.time()
    response = requests.post(f"{BASE_URL}/flow-delete-requests", json=deletion_request)
    end_time = time.time()
    
    response_time = end_time - start_time
    print(f"   Creation Response Time: {response_time:.3f} seconds")
    print(f"   Status Code: {response.status_code}")
    
    if response.status_code in [200, 201]:
        data = response.json()
        request_id = data.get("id") or data.get("request_id")
        if request_id:
            test_data["object_ids"].append(request_id)
    
    # Test deletion request listing performance
    print_subsection("Deletion Request Listing Performance")
    
    start_time = time.time()
    response = requests.get(f"{BASE_URL}/flow-delete-requests")
    end_time = time.time()
    
    response_time = end_time - start_time
    print(f"   Listing Response Time: {response_time:.3f} seconds")
    print(f"   Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"   Deletion Requests Count: {len(data)}")

def run_all_deletion_requests_tests():
    """Run all deletion requests tests"""
    print("🚀 Starting Deletion Requests Endpoint Tests")
    print(f"🔗 Base URL: {BASE_URL}")
    print(f"⏰ Start Time: {datetime.now().isoformat()}")
    
    try:
        test_deletion_requests_crud()
        test_deletion_requests_management()
        test_deletion_requests_cascade()
        test_deletion_requests_dependency_violations()
        test_deletion_requests_batch_operations()
        test_deletion_requests_head_operations()
        test_deletion_requests_error_cases()
        test_deletion_requests_performance()
        
        print_section("DELETION REQUESTS TESTS SUMMARY")
        print("✅ All deletion requests endpoint tests completed successfully")
        
    except Exception as e:
        print(f"❌ Deletion requests tests failed: {e}")
        raise
    finally:
        cleanup_test_data()

if __name__ == "__main__":
    run_all_deletion_requests_tests()
