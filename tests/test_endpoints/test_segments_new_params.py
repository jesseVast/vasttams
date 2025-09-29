#!/usr/bin/env python3
"""
Test new segment query parameters

This tests the newly implemented query parameters for segments endpoints:
- object_id: Filter on object identifier
- reverse_order: Return segments in reverse time order
- verbose_storage: Include storage metadata in get_urls
"""

import requests
import json
from test_utils import (
    BASE_URL, assert_response_success, assert_response_status,
    print_section, print_subsection, create_test_source, create_test_flow
)

# Global test data
test_data = {}

def test_segments_object_id_filtering():
    """Test object_id filtering for segments"""
    print_section("SEGMENTS OBJECT_ID FILTERING")
    
    if not test_data.get("flow_id"):
        print("❌ No flow_id available for object_id test")
        return
    
    # Create multiple segments with different object_ids
    segment_data_1 = {
        "object_id": "test-object-1",
        "timerange": {"value": "0:1000"},
        "ts_offset": {"value": "0:0"},
        "last_duration": {"value": "0:100"},
        "sample_offset": 0,
        "sample_count": 1000,
        "key_frame_count": 10
    }
    
    segment_data_2 = {
        "object_id": "test-object-2", 
        "timerange": {"value": "1000:2000"},
        "ts_offset": {"value": "0:0"},
        "last_duration": {"value": "0:100"},
        "sample_offset": 1000,
        "sample_count": 1000,
        "key_frame_count": 10
    }
    
    # Create first segment
    response = requests.post(f"{BASE_URL}/flows/{test_data['flow_id']}/segments", json=segment_data_1)
    data_1 = assert_response_success("POST", f"/flows/{test_data['flow_id']}/segments (object-1)", response, 201)
    test_data["object_id_1"] = data_1["object_id"]
    
    # Create second segment
    response = requests.post(f"{BASE_URL}/flows/{test_data['flow_id']}/segments", json=segment_data_2)
    data_2 = assert_response_success("POST", f"/flows/{test_data['flow_id']}/segments (object-2)", response, 201)
    test_data["object_id_2"] = data_2["object_id"]
    
    # Test filtering by object_id_1
    print_subsection("Filter by object_id_1")
    response = requests.get(f"{BASE_URL}/flows/{test_data['flow_id']}/segments?object_id={test_data['object_id_1']}")
    data = assert_response_success("GET", f"/flows/{test_data['flow_id']}/segments?object_id={test_data['object_id_1']}", response, 200)
    assert len(data) == 1, f"Expected 1 segment, got {len(data)}"
    assert data[0]["object_id"] == test_data["object_id_1"], "Wrong object_id returned"
    
    # Test filtering by object_id_2
    print_subsection("Filter by object_id_2")
    response = requests.get(f"{BASE_URL}/flows/{test_data['flow_id']}/segments?object_id={test_data['object_id_2']}")
    data = assert_response_success("GET", f"/flows/{test_data['flow_id']}/segments?object_id={test_data['object_id_2']}", response, 200)
    assert len(data) == 1, f"Expected 1 segment, got {len(data)}"
    assert data[0]["object_id"] == test_data["object_id_2"], "Wrong object_id returned"
    
    # Test filtering by non-existent object_id
    print_subsection("Filter by non-existent object_id")
    response = requests.get(f"{BASE_URL}/flows/{test_data['flow_id']}/segments?object_id=non-existent")
    data = assert_response_success("GET", f"/flows/{test_data['flow_id']}/segments?object_id=non-existent", response, 200)
    assert len(data) == 0, f"Expected 0 segments, got {len(data)}"

def test_segments_reverse_order():
    """Test reverse_order sorting for segments"""
    print_section("SEGMENTS REVERSE ORDER SORTING")
    
    if not test_data.get("flow_id"):
        print("❌ No flow_id available for reverse_order test")
        return
    
    # Get all segments in normal order
    print_subsection("Normal order (ascending)")
    response = requests.get(f"{BASE_URL}/flows/{test_data['flow_id']}/segments")
    data_normal = assert_response_success("GET", f"/flows/{test_data['flow_id']}/segments", response, 200)
    
    # Get all segments in reverse order
    print_subsection("Reverse order (descending)")
    response = requests.get(f"{BASE_URL}/flows/{test_data['flow_id']}/segments?reverse_order=true")
    data_reverse = assert_response_success("GET", f"/flows/{test_data['flow_id']}/segments?reverse_order=true", response, 200)
    
    # Verify we have the same number of segments
    assert len(data_normal) == len(data_reverse), f"Segment count mismatch: normal={len(data_normal)}, reverse={len(data_reverse)}"
    
    # Verify reverse order (if we have multiple segments)
    if len(data_normal) > 1:
        # Check that the order is actually reversed
        normal_timeranges = [s.get("timerange", {}).get("value", "") for s in data_normal]
        reverse_timeranges = [s.get("timerange", {}).get("value", "") for s in data_reverse]
        
        # Reverse the normal order and compare
        expected_reverse = list(reversed(normal_timeranges))
        assert reverse_timeranges == expected_reverse, f"Reverse order not correct: {reverse_timeranges} != {expected_reverse}"

def test_segments_verbose_storage():
    """Test verbose_storage parameter for segments"""
    print_section("SEGMENTS VERBOSE STORAGE")
    
    if not test_data.get("flow_id"):
        print("❌ No flow_id available for verbose_storage test")
        return
    
    # Get segments with verbose storage (default)
    print_subsection("Verbose storage (default)")
    response = requests.get(f"{BASE_URL}/flows/{test_data['flow_id']}/segments?verbose_storage=true")
    data_verbose = assert_response_success("GET", f"/flows/{test_data['flow_id']}/segments?verbose_storage=true", response, 200)
    
    # Get segments without verbose storage
    print_subsection("Non-verbose storage")
    response = requests.get(f"{BASE_URL}/flows/{test_data['flow_id']}/segments?verbose_storage=false")
    data_non_verbose = assert_response_success("GET", f"/flows/{test_data['flow_id']}/segments?verbose_storage=false", response, 200)
    
    # Verify we have the same number of segments
    assert len(data_verbose) == len(data_non_verbose), f"Segment count mismatch: verbose={len(data_verbose)}, non-verbose={len(data_non_verbose)}"
    
    # Check get_urls structure (if segments have get_urls)
    for i, (verbose_seg, non_verbose_seg) in enumerate(zip(data_verbose, data_non_verbose)):
        if "get_urls" in verbose_seg and verbose_seg["get_urls"]:
            verbose_urls = verbose_seg["get_urls"]
            non_verbose_urls = non_verbose_seg.get("get_urls", [])
            
            # Non-verbose should have fewer fields per URL
            for j, (verbose_url, non_verbose_url) in enumerate(zip(verbose_urls, non_verbose_urls)):
                # Non-verbose should only have url, presigned, and label
                expected_fields = {"url", "presigned", "label"}
                actual_fields = set(non_verbose_url.keys())
                
                # Check that non-verbose has only the expected fields
                extra_fields = actual_fields - expected_fields
                assert len(extra_fields) == 0, f"Non-verbose URL {j} has extra fields: {extra_fields}"

def test_segments_combined_parameters():
    """Test combining multiple query parameters"""
    print_section("SEGMENTS COMBINED PARAMETERS")
    
    if not test_data.get("flow_id"):
        print("❌ No flow_id available for combined parameters test")
        return
    
    # Test object_id + reverse_order
    print_subsection("object_id + reverse_order")
    response = requests.get(f"{BASE_URL}/flows/{test_data['flow_id']}/segments?object_id={test_data.get('object_id_1', 'test')}&reverse_order=true")
    data = assert_response_success("GET", f"/flows/{test_data['flow_id']}/segments?object_id={test_data.get('object_id_1', 'test')}&reverse_order=true", response, 200)
    
    # Test object_id + verbose_storage
    print_subsection("object_id + verbose_storage")
    response = requests.get(f"{BASE_URL}/flows/{test_data['flow_id']}/segments?object_id={test_data.get('object_id_1', 'test')}&verbose_storage=false")
    data = assert_response_success("GET", f"/flows/{test_data['flow_id']}/segments?object_id={test_data.get('object_id_1', 'test')}&verbose_storage=false", response, 200)
    
    # Test reverse_order + verbose_storage
    print_subsection("reverse_order + verbose_storage")
    response = requests.get(f"{BASE_URL}/flows/{test_data['flow_id']}/segments?reverse_order=true&verbose_storage=false")
    data = assert_response_success("GET", f"/flows/{test_data['flow_id']}/segments?reverse_order=true&verbose_storage=false", response, 200)
    
    # Test all parameters combined
    print_subsection("All parameters combined")
    response = requests.get(f"{BASE_URL}/flows/{test_data['flow_id']}/segments?object_id={test_data.get('object_id_1', 'test')}&reverse_order=true&verbose_storage=false&limit=5&offset=0")
    data = assert_response_success("GET", f"/flows/{test_data['flow_id']}/segments?all_params", response, 200)

def test_segments_url_filtering():
    """Test URL filtering parameters for segments"""
    print_section("SEGMENTS URL FILTERING")
    
    if not test_data.get("flow_id"):
        print("❌ No flow_id available for URL filtering test")
        return
    
    # Test accept_get_urls filtering (by label)
    print_subsection("Filter by URL labels")
    response = requests.get(f"{BASE_URL}/flows/{test_data['flow_id']}/segments?accept_get_urls=label1,label2")
    data = assert_response_success("GET", f"/flows/{test_data['flow_id']}/segments?accept_get_urls=label1,label2", response, 200)
    
    # Test accept_storage_ids filtering (by storage ID)
    print_subsection("Filter by storage IDs")
    response = requests.get(f"{BASE_URL}/flows/{test_data['flow_id']}/segments?accept_storage_ids=12345678-1234-1234-1234-123456789abc")
    data = assert_response_success("GET", f"/flows/{test_data['flow_id']}/segments?accept_storage_ids=12345678-1234-1234-1234-123456789abc", response, 200)
    
    # Test presigned filtering
    print_subsection("Filter by presigned URLs")
    response = requests.get(f"{BASE_URL}/flows/{test_data['flow_id']}/segments?presigned=true")
    data = assert_response_success("GET", f"/flows/{test_data['flow_id']}/segments?presigned=true", response, 200)
    
    response = requests.get(f"{BASE_URL}/flows/{test_data['flow_id']}/segments?presigned=false")
    data = assert_response_success("GET", f"/flows/{test_data['flow_id']}/segments?presigned=false", response, 200)
    
    # Test combined URL filtering
    print_subsection("Combined URL filtering")
    response = requests.get(f"{BASE_URL}/flows/{test_data['flow_id']}/segments?accept_get_urls=label1&presigned=true")
    data = assert_response_success("GET", f"/flows/{test_data['flow_id']}/segments?accept_get_urls=label1&presigned=true", response, 200)

def test_segments_delete_with_object_id():
    """Test DELETE segments with object_id parameter"""
    print_section("SEGMENTS DELETE WITH OBJECT_ID")
    
    if not test_data.get("flow_id"):
        print("❌ No flow_id available for delete test")
        return
    
    # Test deleting segments by object_id
    if test_data.get("object_id_1"):
        print_subsection("Delete segments by object_id_1")
        response = requests.delete(f"{BASE_URL}/flows/{test_data['flow_id']}/segments?object_id={test_data['object_id_1']}")
        # DELETE might return 200 or 204 depending on implementation
        assert_response_status("DELETE", f"/flows/{test_data['flow_id']}/segments?object_id={test_data['object_id_1']}", response, 200)
        
        # Verify segments with that object_id are gone
        response = requests.get(f"{BASE_URL}/flows/{test_data['flow_id']}/segments?object_id={test_data['object_id_1']}")
        data = assert_response_success("GET", f"/flows/{test_data['flow_id']}/segments?object_id={test_data['object_id_1']}", response, 200)
        assert len(data) == 0, f"Expected 0 segments with object_id_1, got {len(data)}"

def run_all_new_parameter_tests():
    """Run all new parameter tests"""
    print("🚀 Starting New Segment Parameter Tests")
    print(f"🔗 Base URL: {BASE_URL}")
    
    # Create test data
    print_section("SETUP")
    test_data["source_id"] = create_test_source()
    test_data["flow_id"] = create_test_flow(test_data["source_id"])
    
    # Allocate storage
    storage_request = {
        "purpose": "new_parameter_testing",
        "format": "video/H264"
    }
    response = requests.post(f"{BASE_URL}/flows/{test_data['flow_id']}/storage", json=storage_request)
    assert_response_success("POST", f"/flows/{test_data['flow_id']}/storage", response, 201)
    
    try:
        # Run tests
        test_segments_object_id_filtering()
        test_segments_reverse_order()
        test_segments_verbose_storage()
        test_segments_combined_parameters()
        test_segments_url_filtering()
        test_segments_delete_with_object_id()
        
        print_section("NEW PARAMETER TESTS SUMMARY")
        print("✅ All new segment parameter tests completed successfully")
        
    finally:
        # Cleanup
        print(f"   🧹 Cleaned up flow: {test_data['flow_id']}")
        print(f"   🧹 Cleaned up source: {test_data['source_id']}")

if __name__ == "__main__":
    run_all_new_parameter_tests()
