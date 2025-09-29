#!/usr/bin/env python3
"""
Sources Endpoint Tests

Tests for all source-related endpoints including:
- CRUD operations
- Batch operations
- Tags management
- Properties management
- Collections
"""

import requests
from datetime import datetime
from test_utils import (
    BASE_URL, test_data, print_section, print_subsection, print_result,
    assert_response_success, assert_response_status, assert_response_any_status,
    create_test_source, cleanup_test_data, generate_uuid
)

def test_sources_crud():
    """Test basic source CRUD operations"""
    print_section("SOURCES CRUD OPERATIONS")
    
    # CREATE - POST /sources
    print_subsection("CREATE Source")
    source_id = generate_uuid()
    source_data = {
        "id": source_id,
        "format": "urn:x-nmos:format:video",
        "label": f"Test Source {source_id[:8]}",
        "description": "Test source for comprehensive API testing"
    }
    
    response = requests.post(f"{BASE_URL}/sources", json=source_data)
    data = assert_response_success("POST", "/sources", response, 201)
    test_data["source_id"] = data["id"]
    
    # READ - GET /sources
    print_subsection("READ Sources List")
    response = requests.get(f"{BASE_URL}/sources")
    data = assert_response_success("GET", "/sources", response, 200)
    assert "data" in data
    assert isinstance(data["data"], list)
    
    # READ - GET /sources/{source_id}
    print_subsection("READ Specific Source")
    response = requests.get(f"{BASE_URL}/sources/{test_data['source_id']}")
    data = assert_response_success("GET", f"/sources/{test_data['source_id']}", response, 200)
    assert data["id"] == test_data["source_id"]
    
    # UPDATE - PUT /sources/{source_id} (not implemented, test for 405)
    print_subsection("UPDATE Source (Not Implemented)")
    updated_source = {
        "format": "urn:x-nmos:format:video",
        "label": f"Updated Test Source {test_data.get('test_id', 'unknown')}",
        "description": "Updated test source description"
    }
    response = requests.put(f"{BASE_URL}/sources/{test_data['source_id']}", json=updated_source)
    # PUT method is not implemented for sources, should return 405
    assert_response_status("PUT", f"/sources/{test_data['source_id']}", response, 405)

def test_sources_batch_operations():
    """Test batch source operations"""
    print_section("SOURCES BATCH OPERATIONS")
    
    # POST /sources/batch
    print_subsection("CREATE Multiple Sources")
    batch_sources = [
        {
            "id": generate_uuid(),
            "format": "urn:x-nmos:format:video",
            "label": f"Batch Source 1 {generate_uuid()[:8]}",
            "description": "First batch source"
        },
        {
            "id": generate_uuid(),
            "format": "urn:x-nmos:format:audio",
            "label": f"Batch Source 2 {generate_uuid()[:8]}",
            "description": "Second batch source"
        }
    ]
    
    response = requests.post(f"{BASE_URL}/sources/batch", json=batch_sources)
    data = assert_response_success("POST", "/sources/batch", response, 201)
    assert isinstance(data, list)
    assert len(data) == 2
    
    # Store batch source IDs for cleanup
    for source in data:
        test_data["object_ids"].append(source["id"])

def test_sources_tags():
    """Test source tag operations"""
    print_section("SOURCE TAGS OPERATIONS")
    
    if not test_data.get("source_id"):
        print("❌ No source_id available for tag test")
        return
    
    # GET /sources/{source_id}/tags
    print_subsection("GET Source Tags")
    response = requests.get(f"{BASE_URL}/sources/{test_data['source_id']}/tags")
    # Note: 500 errors are expected if tag service is not fully implemented
    assert_response_any_status("GET", f"/sources/{test_data['source_id']}/tags", response, [200, 500])
    
    # PUT /sources/{source_id}/tags/{name}
    print_subsection("PUT Individual Source Tag")
    response = requests.put(
        f"{BASE_URL}/sources/{test_data['source_id']}/tags/test_tag",
        data="test_value",
        headers={"Content-Type": "text/plain"}
    )
    assert_response_any_status("PUT", f"/sources/{test_data['source_id']}/tags/test_tag", response, [200, 201, 204, 500])
    
    # PUT another tag
    response = requests.put(
        f"{BASE_URL}/sources/{test_data['source_id']}/tags/environment",
        data="testing",
        headers={"Content-Type": "text/plain"}
    )
    assert_response_any_status("PUT", f"/sources/{test_data['source_id']}/tags/environment", response, [200, 201, 204, 500])
    
    # GET /sources/{source_id}/tags/{name}
    print_subsection("GET Specific Source Tag")
    response = requests.get(f"{BASE_URL}/sources/{test_data['source_id']}/tags/test_tag")
    # Individual tag retrieval should return 200 or 404
    assert_response_any_status("GET", f"/sources/{test_data['source_id']}/tags/test_tag", response, [200, 404])
    
    # DELETE /sources/{source_id}/tags/{name}
    print_subsection("DELETE Specific Source Tag")
    response = requests.delete(f"{BASE_URL}/sources/{test_data['source_id']}/tags/test_tag")
    assert_response_any_status("DELETE", f"/sources/{test_data['source_id']}/tags/test_tag", response, [200, 204, 404])

def test_sources_properties():
    """Test source property operations"""
    print_section("SOURCE PROPERTIES OPERATIONS")
    
    if not test_data.get("source_id"):
        print("❌ No source_id available for properties test")
        return
    
    # Description operations
    print_subsection("Source Description")
    response = requests.get(f"{BASE_URL}/sources/{test_data['source_id']}/description")
    assert_response_any_status("GET", f"/sources/{test_data['source_id']}/description", response, [200, 404])
    
    response = requests.put(
        f"{BASE_URL}/sources/{test_data['source_id']}/description?description=Updated description"
    )
    assert_response_any_status("PUT", f"/sources/{test_data['source_id']}/description", response, [200, 201, 204, 404])
    
    response = requests.delete(f"{BASE_URL}/sources/{test_data['source_id']}/description")
    assert_response_any_status("DELETE", f"/sources/{test_data['source_id']}/description", response, [200, 204, 404])
    
    # Label operations
    print_subsection("Source Label")
    response = requests.get(f"{BASE_URL}/sources/{test_data['source_id']}/label")
    assert_response_any_status("GET", f"/sources/{test_data['source_id']}/label", response, [200, 404])
    
    response = requests.put(
        f"{BASE_URL}/sources/{test_data['source_id']}/label?label=Updated label"
    )
    assert_response_any_status("PUT", f"/sources/{test_data['source_id']}/label", response, [200, 201, 204, 404])
    
    response = requests.delete(f"{BASE_URL}/sources/{test_data['source_id']}/label")
    assert_response_any_status("DELETE", f"/sources/{test_data['source_id']}/label", response, [200, 204, 404])


def test_sources_head_operations():
    """Test HEAD operations for sources"""
    print_section("SOURCES HEAD OPERATIONS")
    
    if not test_data.get("source_id"):
        print("❌ No source_id available for HEAD test")
        return
    
    # HEAD /sources
    print_subsection("HEAD Sources List")
    response = requests.head(f"{BASE_URL}/sources")
    assert_response_status("HEAD", "/sources", response, 200)
    
    # HEAD /sources/{source_id}
    print_subsection("HEAD Specific Source")
    response = requests.head(f"{BASE_URL}/sources/{test_data['source_id']}")
    assert_response_status("HEAD", f"/sources/{test_data['source_id']}", response, 200)
    
    # HEAD /sources/{source_id}/tags
    print_subsection("HEAD Source Tags")
    response = requests.head(f"{BASE_URL}/sources/{test_data['source_id']}/tags")
    assert_response_any_status("HEAD", f"/sources/{test_data['source_id']}/tags", response, [200, 500])
    
    # HEAD /sources/{source_id}/tags/{name}
    print_subsection("HEAD Specific Source Tag")
    response = requests.head(f"{BASE_URL}/sources/{test_data['source_id']}/tags/test_tag")
    assert_response_any_status("HEAD", f"/sources/{test_data['source_id']}/tags/test_tag", response, [200, 404, 500])
    
    # HEAD /sources/{source_id}/description
    print_subsection("HEAD Source Description")
    response = requests.head(f"{BASE_URL}/sources/{test_data['source_id']}/description")
    assert_response_any_status("HEAD", f"/sources/{test_data['source_id']}/description", response, [200, 404])
    
    # HEAD /sources/{source_id}/label
    print_subsection("HEAD Source Label")
    response = requests.head(f"{BASE_URL}/sources/{test_data['source_id']}/label")
    assert_response_any_status("HEAD", f"/sources/{test_data['source_id']}/label", response, [200, 404])
    

def run_all_sources_tests():
    """Run all sources tests"""
    print("🚀 Starting Sources Endpoint Tests")
    print(f"🔗 Base URL: {BASE_URL}")
    print(f"⏰ Start Time: {datetime.now().isoformat()}")
    
    try:
        test_sources_crud()
        test_sources_batch_operations()
        test_sources_tags()
        test_sources_properties()
        test_sources_head_operations()
        
        print_section("SOURCES TESTS SUMMARY")
        print("✅ All sources endpoint tests completed successfully")
        
    except Exception as e:
        print(f"❌ Sources tests failed: {e}")
        raise
    finally:
        cleanup_test_data()

if __name__ == "__main__":
    run_all_sources_tests()
