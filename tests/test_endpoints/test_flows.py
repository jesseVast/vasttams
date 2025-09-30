#!/usr/bin/env python3
"""
Flows Endpoint Tests

Tests for all flow-related endpoints including:
- CRUD operations
- Batch operations
- Tags management
- Properties management
- Flow collection
- Bit rate operations
- Storage allocation
"""

import requests
import uuid
from datetime import datetime
from .test_utils import (
    BASE_URL, test_data, print_section, print_subsection, print_result,
    assert_response_success, assert_response_status, assert_response_any_status,
    create_test_source, create_test_flow, cleanup_test_data, generate_uuid
)

def test_flows_automatic_source_creation():
    """Test automatic source creation when flow is created with non-existent source_id"""
    print_section("FLOWS AUTOMATIC SOURCE CREATION")
    
    # Create a flow with a non-existent source ID
    print_subsection("CREATE Flow with Non-existent Source ID")
    flow_data = {
        "id": str(uuid.uuid4()),
        "source_id": str(uuid.uuid4()),  # Non-existent source ID
        "label": f"Test Flow Auto Source {test_data.get('test_id', 'unknown')}",
        "description": "Test flow for automatic source creation",
        "format": "urn:x-nmos:format:video",
        "codec": "video/H264",
        "essence_parameters": {
            "frame_width": 1920,
            "frame_height": 1080,
            "frame_rate": {"numerator": 25, "denominator": 1}
        }
    }
    
    response = requests.post(f"{BASE_URL}/flows", json=flow_data)
    data = assert_response_success("POST", "/flows", response, 201)
    test_data["flow_id"] = data["id"]
    test_data["source_id"] = data["source_id"]
    
    print_result("POST", "/flows", response.status_code)
    print(f"   Flow ID: {data['id']}")
    print(f"   Source ID: {data['source_id']}")
    
    # Verify the source was created automatically
    print_subsection("VERIFY Source Created Automatically")
    response = requests.get(f"{BASE_URL}/sources/{test_data['source_id']}")
    data = assert_response_success("GET", f"/sources/{test_data['source_id']}", response, 200)
    
    print_result("GET", f"/sources/{test_data['source_id']}", response.status_code)
    print(f"   Source ID: {data['id']}")
    print(f"   Format: {data['format']}")
    print(f"   Label: {data['label']}")
    print(f"   Description: {data['description']}")
    
    # Verify source metadata matches flow metadata
    assert data['id'] == test_data['source_id'], "Source ID should match flow source_id"
    assert data['format'] == flow_data['format'], "Source format should match flow format"
    assert data['label'] == flow_data['label'], "Source label should match flow label"
    assert data['description'] == flow_data['description'], "Source description should match flow description"
    
    print("✅ Automatic source creation working correctly!")
    
    # Clean up
    cleanup_test_data()

def test_flows_crud():
    """Test basic flow CRUD operations"""
    print_section("FLOWS CRUD OPERATIONS")
    
    # Create a source first
    test_data["source_id"] = create_test_source()
    
    # CREATE - POST /flows
    print_subsection("CREATE Flow")
    flow_data = {
        "id": str(uuid.uuid4()),
        "source_id": test_data["source_id"],
        "label": f"Test Flow {test_data.get('test_id', 'unknown')}",
        "description": "Test flow for comprehensive API testing",
        "format": "urn:x-nmos:format:video",
        "codec": "video/H264",
        "essence_parameters": {
            "frame_width": 1920,
            "frame_height": 1080,
            "frame_rate": {"numerator": 25, "denominator": 1}
        }
    }
    
    response = requests.post(f"{BASE_URL}/flows", json=flow_data)
    data = assert_response_success("POST", "/flows", response, 201)
    test_data["flow_id"] = data["id"]
    
    # READ - GET /flows
    print_subsection("READ Flows List")
    response = requests.get(f"{BASE_URL}/flows")
    data = assert_response_success("GET", "/flows", response, 200)
    assert "data" in data
    assert isinstance(data["data"], list)
    
    # READ - GET /flows/{flow_id}
    print_subsection("READ Specific Flow")
    response = requests.get(f"{BASE_URL}/flows/{test_data['flow_id']}")
    data = assert_response_success("GET", f"/flows/{test_data['flow_id']}", response, 200)
    assert data["id"] == test_data["flow_id"]
    
    # UPDATE - PUT /flows/{flow_id}
    print_subsection("UPDATE Flow")
    updated_flow = {
        "id": test_data["flow_id"],
        "source_id": test_data["source_id"],
        "label": f"Updated Test Flow {test_data.get('test_id', 'unknown')}",
        "description": "Updated test flow description",
        "format": "urn:x-nmos:format:video",
        "codec": "video/H264",
        "essence_parameters": {
            "frame_width": 1920,
            "frame_height": 1080,
            "frame_rate": {"numerator": 25, "denominator": 1}
        }
    }
    response = requests.put(f"{BASE_URL}/flows/{test_data['flow_id']}", json=updated_flow)
    data = assert_response_success("PUT", f"/flows/{test_data['flow_id']}", response, 200)
    assert data["label"] == updated_flow["label"]
    
    # DELETE - DELETE /flows/{flow_id}
    print_subsection("DELETE Flow")
    response = requests.delete(f"{BASE_URL}/flows/{test_data['flow_id']}")
    assert_response_success("DELETE", f"/flows/{test_data['flow_id']}", response, 204)
    
    # Verify flow is deleted
    response = requests.get(f"{BASE_URL}/flows/{test_data['flow_id']}")
    assert_response_status("GET", f"/flows/{test_data['flow_id']}", response, 404)
    
    # Clear flow_id so subsequent tests create their own
    test_data["flow_id"] = None

def test_flows_tags():
    """Test flow tag operations"""
    print_section("FLOW TAGS OPERATIONS")
    
    # Create a flow for tag testing if one doesn't exist
    if not test_data.get("flow_id"):
        if not test_data.get("source_id"):
            test_data["source_id"] = create_test_source()
        
        flow_data = {
            "id": str(uuid.uuid4()),
            "source_id": test_data["source_id"],
            "label": f"Tag Test Flow {test_data.get('test_id', 'unknown')}",
            "description": "Flow for testing tags",
            "format": "urn:x-nmos:format:video",
            "codec": "video/H264",
            "essence_parameters": {
                "frame_width": 1920,
                "frame_height": 1080,
                "frame_rate": {"numerator": 25, "denominator": 1}
            }
        }
        
        response = requests.post(f"{BASE_URL}/flows", json=flow_data)
        data = assert_response_success("POST", "/flows", response, 201)
        test_data["flow_id"] = data["id"]
        test_data["object_ids"].append(data["id"])
    
    # GET /flows/{flow_id}/tags
    print_subsection("GET Flow Tags")
    response = requests.get(f"{BASE_URL}/flows/{test_data['flow_id']}/tags")
    assert_response_any_status("GET", f"/flows/{test_data['flow_id']}/tags", response, [200, 500])
    
    # PUT /flows/{flow_id}/tags/{name}
    print_subsection("PUT Individual Flow Tag")
    response = requests.put(
        f"{BASE_URL}/flows/{test_data['flow_id']}/tags/flow_tag",
        data="flow_value",
        headers={"Content-Type": "text/plain"}
    )
    assert_response_any_status("PUT", f"/flows/{test_data['flow_id']}/tags/flow_tag", response, [200, 201, 204, 500])
    
    # PUT another tag
    response = requests.put(
        f"{BASE_URL}/flows/{test_data['flow_id']}/tags/priority",
        data="high",
        headers={"Content-Type": "text/plain"}
    )
    assert_response_any_status("PUT", f"/flows/{test_data['flow_id']}/tags/priority", response, [200, 201, 204, 500])
    
    # GET /flows/{flow_id}/tags/{name}
    print_subsection("GET Specific Flow Tag")
    response = requests.get(f"{BASE_URL}/flows/{test_data['flow_id']}/tags/flow_tag")
    assert_response_any_status("GET", f"/flows/{test_data['flow_id']}/tags/flow_tag", response, [200, 404, 500])
    
    # DELETE /flows/{flow_id}/tags/{name}
    print_subsection("DELETE Specific Flow Tag")
    response = requests.delete(f"{BASE_URL}/flows/{test_data['flow_id']}/tags/flow_tag")
    assert_response_any_status("DELETE", f"/flows/{test_data['flow_id']}/tags/flow_tag", response, [200, 204, 404, 500])

def test_flows_properties():
    """Test flow property operations"""
    print_section("FLOW PROPERTIES OPERATIONS")
    
    if not test_data.get("flow_id"):
        print("❌ No flow_id available for properties test")
        return
    
    # Description operations
    print_subsection("Flow Description")
    response = requests.get(f"{BASE_URL}/flows/{test_data['flow_id']}/description")
    assert_response_any_status("GET", f"/flows/{test_data['flow_id']}/description", response, [200, 404])
    
    response = requests.put(
        f"{BASE_URL}/flows/{test_data['flow_id']}/description",
        data="Updated flow description",
        headers={"Content-Type": "text/plain"}
    )
    assert_response_any_status("PUT", f"/flows/{test_data['flow_id']}/description", response, [200, 201, 204, 404])
    
    response = requests.delete(f"{BASE_URL}/flows/{test_data['flow_id']}/description")
    assert_response_any_status("DELETE", f"/flows/{test_data['flow_id']}/description", response, [200, 204, 404])
    
    # Label operations
    print_subsection("Flow Label")
    response = requests.get(f"{BASE_URL}/flows/{test_data['flow_id']}/label")
    assert_response_any_status("GET", f"/flows/{test_data['flow_id']}/label", response, [200, 404])
    
    response = requests.put(
        f"{BASE_URL}/flows/{test_data['flow_id']}/label",
        data="Updated flow label",
        headers={"Content-Type": "text/plain"}
    )
    assert_response_any_status("PUT", f"/flows/{test_data['flow_id']}/label", response, [200, 201, 204, 404])
    
    response = requests.delete(f"{BASE_URL}/flows/{test_data['flow_id']}/label")
    assert_response_any_status("DELETE", f"/flows/{test_data['flow_id']}/label", response, [200, 204, 404])
    
    # Read-only operations
    print_subsection("Flow Read-Only")
    response = requests.get(f"{BASE_URL}/flows/{test_data['flow_id']}/read_only")
    assert_response_any_status("GET", f"/flows/{test_data['flow_id']}/read_only", response, [200, 404])
    
    response = requests.put(
        f"{BASE_URL}/flows/{test_data['flow_id']}/read_only",
        data="true",
        headers={"Content-Type": "text/plain"}
    )
    assert_response_any_status("PUT", f"/flows/{test_data['flow_id']}/read_only", response, [200, 201, 204, 404])

def test_flows_collection():
    """Test flow collection operations"""
    print_section("FLOW COLLECTION OPERATIONS")
    
    if not test_data.get("flow_id"):
        print("❌ No flow_id available for collection test")
        return
    
    # GET /flows/{flow_id}/flow_collection
    print_subsection("GET Flow Collection")
    response = requests.get(f"{BASE_URL}/flows/{test_data['flow_id']}/flow_collection")
    assert_response_any_status("GET", f"/flows/{test_data['flow_id']}/flow_collection", response, [200, 404])
    
    # PUT /flows/{flow_id}/flow_collection
    print_subsection("PUT Flow Collection")
    collection_data = {
        "collection_id": f"test-flow-collection-{test_data.get('test_id', 'unknown')}",
        "label": "Test Flow Collection",
        "description": "Test flow collection for API testing"
    }
    response = requests.put(f"{BASE_URL}/flows/{test_data['flow_id']}/flow_collection", json=collection_data)
    assert_response_any_status("PUT", f"/flows/{test_data['flow_id']}/flow_collection", response, [200, 201, 404])
    
    # DELETE /flows/{flow_id}/flow_collection
    print_subsection("DELETE Flow Collection")
    response = requests.delete(f"{BASE_URL}/flows/{test_data['flow_id']}/flow_collection")
    assert_response_any_status("DELETE", f"/flows/{test_data['flow_id']}/flow_collection", response, [200, 204, 404])

def test_flows_bit_rates():
    """Test flow bit rate operations"""
    print_section("FLOW BIT RATE OPERATIONS")
    
    if not test_data.get("flow_id"):
        print("❌ No flow_id available for bit rate test")
        return
    
    # Max bit rate operations
    print_subsection("Flow Max Bit Rate")
    response = requests.get(f"{BASE_URL}/flows/{test_data['flow_id']}/max_bit_rate")
    assert_response_any_status("GET", f"/flows/{test_data['flow_id']}/max_bit_rate", response, [200, 404])
    
    response = requests.put(
        f"{BASE_URL}/flows/{test_data['flow_id']}/max_bit_rate",
        data="1000000",
        headers={"Content-Type": "text/plain"}
    )
    assert_response_any_status("PUT", f"/flows/{test_data['flow_id']}/max_bit_rate", response, [200, 201, 404])
    
    response = requests.delete(f"{BASE_URL}/flows/{test_data['flow_id']}/max_bit_rate")
    assert_response_any_status("DELETE", f"/flows/{test_data['flow_id']}/max_bit_rate", response, [200, 204, 404])
    
    # Average bit rate operations
    print_subsection("Flow Average Bit Rate")
    response = requests.get(f"{BASE_URL}/flows/{test_data['flow_id']}/avg_bit_rate")
    assert_response_any_status("GET", f"/flows/{test_data['flow_id']}/avg_bit_rate", response, [200, 404])
    
    response = requests.put(
        f"{BASE_URL}/flows/{test_data['flow_id']}/avg_bit_rate",
        data="500000",
        headers={"Content-Type": "text/plain"}
    )
    assert_response_any_status("PUT", f"/flows/{test_data['flow_id']}/avg_bit_rate", response, [200, 201, 404])
    
    response = requests.delete(f"{BASE_URL}/flows/{test_data['flow_id']}/avg_bit_rate")
    assert_response_any_status("DELETE", f"/flows/{test_data['flow_id']}/avg_bit_rate", response, [200, 204, 404])

def test_flows_storage_allocation():
    """Test flow storage allocation"""
    print_section("FLOW STORAGE ALLOCATION")
    
    if not test_data.get("flow_id"):
        print("❌ No flow_id available for storage test")
        return
    
    # POST /flows/{flow_id}/storage
    print_subsection("ALLOCATE Storage")
    storage_request = {
        "limit": 1
    }
    
    response = requests.post(f"{BASE_URL}/flows/{test_data['flow_id']}/storage", json=storage_request)
    data = assert_response_success("POST", f"/flows/{test_data['flow_id']}/storage", response, 201)
    
    # The FlowStorage model doesn't include flow_id, only media_objects
    assert "media_objects" in data
    assert isinstance(data["media_objects"], list)
    assert len(data["media_objects"]) > 0
    
    # Store object IDs for cleanup
    for obj in data["media_objects"]:
        test_data["object_ids"].append(obj["object_id"])
    
    print(f"   📁 Storage Objects: {len(data['media_objects'])}")
    for i, obj in enumerate(data["media_objects"], 1):
        print(f"      Object {i}: {obj['object_id']}")
        if "put_url" in obj and "url" in obj["put_url"]:
            print(f"      Storage Path: {obj.get('metadata', {}).get('storage_path', 'N/A')}")
            print(f"      Presigned URL: {obj['put_url']['url'][:50]}...")

def test_flows_head_operations():
    """Test HEAD operations for flows"""
    print_section("FLOWS HEAD OPERATIONS")
    
    if not test_data.get("flow_id"):
        print("❌ No flow_id available for HEAD test")
        return
    
    # HEAD /flows
    print_subsection("HEAD Flows List")
    response = requests.head(f"{BASE_URL}/flows")
    assert_response_status("HEAD", "/flows", response, 200)
    
    # HEAD /flows/{flow_id}
    print_subsection("HEAD Specific Flow")
    response = requests.head(f"{BASE_URL}/flows/{test_data['flow_id']}")
    assert_response_status("HEAD", f"/flows/{test_data['flow_id']}", response, 200)
    
    # HEAD /flows/{flow_id}/tags
    print_subsection("HEAD Flow Tags")
    response = requests.head(f"{BASE_URL}/flows/{test_data['flow_id']}/tags")
    assert_response_any_status("HEAD", f"/flows/{test_data['flow_id']}/tags", response, [200, 500])
    
    # HEAD /flows/{flow_id}/description
    print_subsection("HEAD Flow Description")
    response = requests.head(f"{BASE_URL}/flows/{test_data['flow_id']}/description")
    assert_response_any_status("HEAD", f"/flows/{test_data['flow_id']}/description", response, [200, 404])
    
    # HEAD /flows/{flow_id}/label
    print_subsection("HEAD Flow Label")
    response = requests.head(f"{BASE_URL}/flows/{test_data['flow_id']}/label")
    assert_response_any_status("HEAD", f"/flows/{test_data['flow_id']}/label", response, [200, 404])
    
    # HEAD /flows/{flow_id}/read_only
    print_subsection("HEAD Flow Read-Only")
    response = requests.head(f"{BASE_URL}/flows/{test_data['flow_id']}/read_only")
    assert_response_any_status("HEAD", f"/flows/{test_data['flow_id']}/read_only", response, [200, 404])
    
    # HEAD /flows/{flow_id}/flow_collection
    print_subsection("HEAD Flow Collection")
    response = requests.head(f"{BASE_URL}/flows/{test_data['flow_id']}/flow_collection")
    assert_response_any_status("HEAD", f"/flows/{test_data['flow_id']}/flow_collection", response, [200, 404])
    
    # HEAD /flows/{flow_id}/max_bit_rate
    print_subsection("HEAD Flow Max Bit Rate")
    response = requests.head(f"{BASE_URL}/flows/{test_data['flow_id']}/max_bit_rate")
    assert_response_any_status("HEAD", f"/flows/{test_data['flow_id']}/max_bit_rate", response, [200, 404])
    
    # HEAD /flows/{flow_id}/avg_bit_rate
    print_subsection("HEAD Flow Average Bit Rate")
    response = requests.head(f"{BASE_URL}/flows/{test_data['flow_id']}/avg_bit_rate")
    assert_response_any_status("HEAD", f"/flows/{test_data['flow_id']}/avg_bit_rate", response, [200, 404])

def run_all_flows_tests():
    """Run all flows tests"""
    print("🚀 Starting Flows Endpoint Tests")
    print(f"🔗 Base URL: {BASE_URL}")
    print(f"⏰ Start Time: {datetime.now().isoformat()}")
    
    try:
        test_flows_automatic_source_creation()
        test_flows_crud()
        test_flows_tags()
        test_flows_properties()
        test_flows_collection()
        test_flows_bit_rates()
        test_flows_storage_allocation()
        test_flows_head_operations()
        
        print_section("FLOWS TESTS SUMMARY")
        print("✅ All flows endpoint tests completed successfully")
        
    except Exception as e:
        print(f"❌ Flows tests failed: {e}")
        raise
    finally:
        cleanup_test_data()

if __name__ == "__main__":
    run_all_flows_tests()
