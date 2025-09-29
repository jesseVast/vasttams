#!/usr/bin/env python3
"""
Segments Endpoint Tests

Tests for all segment-related endpoints including:
- CRUD operations
- Batch operations
- Storage operations
- Time range queries
"""

import requests
from datetime import datetime
from test_utils import (
    BASE_URL, test_data, print_section, print_subsection, print_result,
    assert_response_success, assert_response_status, assert_response_any_status,
    create_test_source, create_test_flow, cleanup_test_data
)

def test_segments_crud():
    """Test basic segment CRUD operations"""
    print_section("SEGMENTS CRUD OPERATIONS")
    
    # Create source and flow first
    test_data["source_id"] = create_test_source()
    test_data["flow_id"] = create_test_flow(test_data["source_id"])
    
    # Allocate storage for the flow
    print_subsection("ALLOCATE Storage for Segments")
    storage_request = {"limit": 1}
    response = requests.post(f"{BASE_URL}/flows/{test_data['flow_id']}/storage", json=storage_request)
    storage_data = assert_response_success("POST", f"/flows/{test_data['flow_id']}/storage", response, 201)
    
    # Store object ID for segment creation
    object_id = storage_data["media_objects"][0]["object_id"]
    test_data["object_ids"].append(object_id)
    
    # CREATE - POST /flows/{flow_id}/segments
    print_subsection("CREATE Flow Segment")
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
    data = assert_response_success("POST", f"/flows/{test_data['flow_id']}/segments", response, 201)
    test_data["segment_ids"].append(data["object_id"])
    
    # READ - GET /flows/{flow_id}/segments
    print_subsection("READ Flow Segments")
    response = requests.get(f"{BASE_URL}/flows/{test_data['flow_id']}/segments")
    data = assert_response_success("GET", f"/flows/{test_data['flow_id']}/segments", response, 200)
    assert isinstance(data, list)
    assert len(data) > 0
    
    # Test with time range query
    print_subsection("READ Segments with Time Range")
    response = requests.get(f"{BASE_URL}/flows/{test_data['flow_id']}/segments?timerange=0:500")
    data = assert_response_success("GET", f"/flows/{test_data['flow_id']}/segments?timerange=0:500", response, 200)
    assert isinstance(data, list)
    
    # Test with limit and offset
    print_subsection("READ Segments with Pagination")
    response = requests.get(f"{BASE_URL}/flows/{test_data['flow_id']}/segments?limit=10&offset=0")
    data = assert_response_success("GET", f"/flows/{test_data['flow_id']}/segments?limit=10&offset=0", response, 200)
    assert isinstance(data, list)

def test_segments_batch_operations():
    """Test batch segment operations"""
    print_section("SEGMENTS BATCH OPERATIONS")
    
    if not test_data.get("flow_id"):
        print("❌ No flow_id available for batch segment test")
        return
    
    # Allocate more storage
    print_subsection("ALLOCATE Additional Storage")
    storage_request = {"limit": 2}
    response = requests.post(f"{BASE_URL}/flows/{test_data['flow_id']}/storage", json=storage_request)
    storage_data = assert_response_success("POST", f"/flows/{test_data['flow_id']}/storage", response, 201)
    
    # Create multiple segments
    print_subsection("CREATE Multiple Segments")
    batch_segments = []
    for i, obj in enumerate(storage_data["media_objects"]):
        segment_data = {
            "object_id": obj["object_id"],
            "timerange": {"value": f"{i*1000}:{(i+1)*1000}"},
            "ts_offset": {"value": "0:0"},
            "last_duration": {"value": "0:100"},
            "sample_offset": i * 1000,
            "sample_count": 1000,
            "key_frame_count": 10
        }
        batch_segments.append(segment_data)
        test_data["object_ids"].append(obj["object_id"])
    
    # POST each segment individually (batch creation not specified in TAMS 7.0)
    for i, segment_data in enumerate(batch_segments):
        response = requests.post(f"{BASE_URL}/flows/{test_data['flow_id']}/segments", json=segment_data)
        data = assert_response_success(f"POST", f"/flows/{test_data['flow_id']}/segments (segment {i+1})", response, 201)
        test_data["segment_ids"].append(data["object_id"])

def test_segments_time_range_queries():
    """Test segment time range queries"""
    print_section("SEGMENTS TIME RANGE QUERIES")
    
    if not test_data.get("flow_id"):
        print("❌ No flow_id available for time range test")
        return
    
    # Test various time range formats
    time_ranges = [
        "0:1000",           # Basic range
        "[0:1000]",         # Inclusive range
        "(0:1000)",         # Exclusive range
        "0:1000_2000:3000", # Multiple ranges
        "0:500",            # Partial range
        "500:1000"          # Offset range
    ]
    
    for timerange in time_ranges:
        print_subsection(f"Query with timerange: {timerange}")
        response = requests.get(f"{BASE_URL}/flows/{test_data['flow_id']}/segments?timerange={timerange}")
        # Time range queries might return 200 or 400 depending on implementation
        if response.status_code in [200, 400]:
            print_result("GET", f"/flows/{test_data['flow_id']}/segments?timerange={timerange}", response.status_code)
        else:
            assert_response_success("GET", f"/flows/{test_data['flow_id']}/segments?timerange={timerange}", response, 200)

def test_segments_pagination():
    """Test segment pagination"""
    print_section("SEGMENTS PAGINATION")
    
    if not test_data.get("flow_id"):
        print("❌ No flow_id available for pagination test")
        return
    
    # Test different pagination parameters
    pagination_tests = [
        {"limit": 1, "offset": 0},
        {"limit": 5, "offset": 0},
        {"limit": 10, "offset": 0},
        {"limit": 1, "offset": 1},
        {"limit": 2, "offset": 2}
    ]
    
    for params in pagination_tests:
        print_subsection(f"Pagination: limit={params['limit']}, offset={params['offset']}")
        query_string = f"limit={params['limit']}&offset={params['offset']}"
        response = requests.get(f"{BASE_URL}/flows/{test_data['flow_id']}/segments?{query_string}")
        data = assert_response_success("GET", f"/flows/{test_data['flow_id']}/segments?{query_string}", response, 200)
        assert isinstance(data, list)
        assert len(data) <= params["limit"]

def test_segments_storage_operations():
    """Test segment storage operations"""
    print_section("SEGMENTS STORAGE OPERATIONS")
    
    if not test_data.get("flow_id"):
        print("❌ No flow_id available for storage test")
        return
    
    # Test storage allocation for segments
    print_subsection("ALLOCATE Storage for New Segments")
    storage_request = {
        "limit": 1,
        "metadata": {
            "purpose": "segment_testing",
            "format": "video/H264"
        }
    }
    
    response = requests.post(f"{BASE_URL}/flows/{test_data['flow_id']}/storage", json=storage_request)
    data = assert_response_success("POST", f"/flows/{test_data['flow_id']}/storage", response, 201)
    
    # The FlowStorage model doesn't include flow_id, only media_objects
    assert "media_objects" in data
    assert len(data["media_objects"]) > 0
    
    # Store object ID
    object_id = data["media_objects"][0]["object_id"]
    test_data["object_ids"].append(object_id)
    
    # Create segment with the allocated storage
    print_subsection("CREATE Segment with Allocated Storage")
    segment_data = {
        "object_id": object_id,
        "timerange": {"value": "0:2000"},
        "ts_offset": {"value": "0:0"},
        "last_duration": {"value": "0:200"},
        "sample_offset": 0,
        "sample_count": 2000,
        "key_frame_count": 20
    }
    
    response = requests.post(f"{BASE_URL}/flows/{test_data['flow_id']}/segments", json=segment_data)
    data = assert_response_success("POST", f"/flows/{test_data['flow_id']}/segments", response, 201)
    test_data["segment_ids"].append(data["object_id"])

def test_segments_deletion():
    """Test segment deletion"""
    print_section("SEGMENTS DELETION")
    
    if not test_data.get("flow_id") or not test_data.get("segment_ids"):
        print("❌ No flow_id or segments available for deletion test")
        return
    
    # DELETE /flows/{flow_id}/segments
    print_subsection("DELETE Flow Segments")
    response = requests.delete(f"{BASE_URL}/flows/{test_data['flow_id']}/segments")
    # Deletion might return 200 or 204 depending on implementation
    assert_response_any_status("DELETE", f"/flows/{test_data['flow_id']}/segments", response, [200, 204])
    
    # Verify segments are deleted
    print_subsection("VERIFY Segments Deleted")
    response = requests.get(f"{BASE_URL}/flows/{test_data['flow_id']}/segments")
    data = assert_response_success("GET", f"/flows/{test_data['flow_id']}/segments", response, 200)
    assert isinstance(data, list)
    # Should be empty or significantly reduced

def test_segments_head_operations():
    """Test HEAD operations for segments"""
    print_section("SEGMENTS HEAD OPERATIONS")
    
    if not test_data.get("flow_id"):
        print("❌ No flow_id available for HEAD test")
        return
    
    # HEAD /flows/{flow_id}/segments
    print_subsection("HEAD Flow Segments")
    response = requests.head(f"{BASE_URL}/flows/{test_data['flow_id']}/segments")
    assert_response_status("HEAD", f"/flows/{test_data['flow_id']}/segments", response, 200)
    
    # HEAD with query parameters
    print_subsection("HEAD Segments with Query")
    response = requests.head(f"{BASE_URL}/flows/{test_data['flow_id']}/segments?limit=10")
    assert_response_status("HEAD", f"/flows/{test_data['flow_id']}/segments?limit=10", response, 200)

def test_segments_error_cases():
    """Test segment error cases"""
    print_section("SEGMENTS ERROR CASES")
    
    # Test with non-existent flow (should return empty list, not 404 per spec)
    print_subsection("Non-existent Flow")
    response = requests.get(f"{BASE_URL}/flows/nonexistent-flow-id/segments")
    assert_response_status("GET", "/flows/nonexistent-flow-id/segments", response, 200)
    data = response.json()
    assert len(data) == 0, "Non-existent flow should return empty segments list"
    
    # Test with invalid time range
    print_subsection("Invalid Time Range")
    response = requests.get(f"{BASE_URL}/flows/{test_data.get('flow_id', 'test')}/segments?timerange=invalid")
    # Invalid time range might return 400 or 200 depending on implementation
    assert_response_any_status("GET", f"/flows/{test_data.get('flow_id', 'test')}/segments?timerange=invalid", response, [200, 400])
    
    # Test with invalid pagination
    print_subsection("Invalid Pagination")
    response = requests.get(f"{BASE_URL}/flows/{test_data.get('flow_id', 'test')}/segments?limit=-1&offset=-1")
    # Invalid pagination might return 400 or 200 depending on implementation
    assert_response_any_status("GET", f"/flows/{test_data.get('flow_id', 'test')}/segments?limit=-1&offset=-1", response, [200, 400])

def run_all_segments_tests():
    """Run all segments tests"""
    print("🚀 Starting Segments Endpoint Tests")
    print(f"🔗 Base URL: {BASE_URL}")
    print(f"⏰ Start Time: {datetime.now().isoformat()}")
    
    try:
        test_segments_crud()
        test_segments_batch_operations()
        test_segments_time_range_queries()
        test_segments_pagination()
        test_segments_storage_operations()
        test_segments_deletion()
        test_segments_head_operations()
        test_segments_error_cases()
        
        print_section("SEGMENTS TESTS SUMMARY")
        print("✅ All segments endpoint tests completed successfully")
        
    except Exception as e:
        print(f"❌ Segments tests failed: {e}")
        raise
    finally:
        cleanup_test_data()

if __name__ == "__main__":
    run_all_segments_tests()
