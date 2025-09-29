#!/usr/bin/env python3
"""
Objects Endpoint Tests

Tests for all object-related endpoints including:
- Object information retrieval
- Object deletion
- Upload URL validation
- Object metadata
"""

import requests
import uuid
from datetime import datetime
from test_utils import (
    BASE_URL, test_data, print_section, print_subsection, print_result,
    assert_response_success, assert_response_status, assert_response_any_status,
    create_test_source, create_test_flow, cleanup_test_data
)

def test_objects_crud():
    """Test basic object CRUD operations"""
    print_section("OBJECTS CRUD OPERATIONS")
    
    # Create source and flow first
    test_data["source_id"] = create_test_source()
    test_data["flow_id"] = create_test_flow(test_data["source_id"])
    
    # CREATE - POST /objects
    print_subsection("CREATE Single Object")
    object_data = {
        "object_id": str(uuid.uuid4()),
        "flow_id": test_data["flow_id"],
        "metadata": {
            "content_type": "video/mp4",
            "size_bytes": 1024000,
            "created_at": datetime.now().isoformat()
        }
    }
    response = requests.post(f"{BASE_URL}/objects", json=object_data)
    data = assert_response_success("POST", "/objects", response, 201)
    test_data["object_ids"].append(data["object_id"])
    
    # CREATE - POST /objects/batch
    print_subsection("CREATE Multiple Objects")
    batch_objects = [
        {
            "object_id": str(uuid.uuid4()),
            "flow_id": test_data["flow_id"],
            "metadata": {
                "content_type": "video/mp4",
                "size_bytes": 2048000
            }
        },
        {
            "object_id": str(uuid.uuid4()),
            "flow_id": test_data["flow_id"],
            "metadata": {
                "content_type": "video/mp4",
                "size_bytes": 3072000
            }
        }
    ]
    response = requests.post(f"{BASE_URL}/objects/batch", json=batch_objects)
    data = assert_response_success("POST", "/objects/batch", response, 201)
    for obj in data["objects"]:
        test_data["object_ids"].append(obj["object_id"])
    
    # Allocate storage to get objects
    print_subsection("ALLOCATE Storage for Objects")
    storage_request = {"limit": 2}
    response = requests.post(f"{BASE_URL}/flows/{test_data['flow_id']}/storage", json=storage_request)
    storage_data = assert_response_success("POST", f"/flows/{test_data['flow_id']}/storage", response, 201)
    
    # Store object IDs
    for obj in storage_data["media_objects"]:
        test_data["object_ids"].append(obj["object_id"])
    
    # READ - GET /objects/{object_id}
    print_subsection("READ Object Information")
    for i, object_id in enumerate(test_data["object_ids"], 1):
        response = requests.get(f"{BASE_URL}/objects/{object_id}")
        data = assert_response_success("GET", f"/objects/{object_id}", response, 200)
        
        assert "object_id" in data
        assert data["object_id"] == object_id
        print(f"   Object {i}: {object_id}")
        
        # Check for metadata
        if "metadata" in data:
            print(f"      Metadata: {data['metadata']}")
        
        # Check for get_urls
        if "get_urls" in data and data["get_urls"]:
            print(f"      Get URLs: {len(data['get_urls'])} available")
            for j, url_info in enumerate(data["get_urls"], 1):
                if "url" in url_info:
                    print(f"         URL {j}: {url_info['url'][:50]}...")

def test_objects_upload_urls():
    """Test object upload URL functionality"""
    print_section("OBJECTS UPLOAD URLS")
    
    if not test_data.get("object_ids"):
        print("❌ No object_ids available for upload URL test")
        return
    
    # Test upload URLs for each object
    for i, object_id in enumerate(test_data["object_ids"], 1):
        print_subsection(f"Upload URL for Object {i}")
        
        # Get object info to check for put_url
        response = requests.get(f"{BASE_URL}/objects/{object_id}")
        data = assert_response_success("GET", f"/objects/{object_id}", response, 200)
        
        if "put_url" in data and data["put_url"]:
            put_url_info = data["put_url"]
            print(f"   Object: {object_id}")
            print(f"   Put URL: {put_url_info.get('url', 'N/A')[:50]}...")
            print(f"   Method: {put_url_info.get('method', 'N/A')}")
            print(f"   Headers: {put_url_info.get('headers', {})}")
            
            # Test if URL is accessible (HEAD request)
            if "url" in put_url_info:
                try:
                    head_response = requests.head(put_url_info["url"], timeout=5)
                    print(f"   URL Status: {head_response.status_code}")
                except Exception as e:
                    print(f"   URL Test Error: {e}")
        else:
            print(f"   No put_url available for object {object_id}")

def test_objects_metadata():
    """Test object metadata operations"""
    print_section("OBJECTS METADATA")
    
    if not test_data.get("object_ids"):
        print("❌ No object_ids available for metadata test")
        return
    
    # Test metadata for each object
    for i, object_id in enumerate(test_data["object_ids"], 1):
        print_subsection(f"Metadata for Object {i}")
        
        response = requests.get(f"{BASE_URL}/objects/{object_id}")
        data = assert_response_success("GET", f"/objects/{object_id}", response, 200)
        
        # Check for various metadata fields
        metadata_fields = [
            "storage_path", "content_type", "content_length", 
            "last_modified", "etag", "checksum", "format"
        ]
        
        print(f"   Object: {object_id}")
        if "metadata" in data:
            metadata = data["metadata"]
            for field in metadata_fields:
                if field in metadata:
                    print(f"      {field}: {metadata[field]}")
        else:
            print("      No metadata available")

def test_objects_deletion():
    """Test object deletion"""
    print_section("OBJECTS DELETION")
    
    if not test_data.get("object_ids"):
        print("❌ No object_ids available for deletion test")
        return
    
    # Test deletion of each object
    for i, object_id in enumerate(test_data["object_ids"], 1):
        print_subsection(f"DELETE Object {i}")
        
        response = requests.delete(f"{BASE_URL}/objects/{object_id}")
        # Deletion might return 200 or 204 depending on implementation
        assert_response_any_status("DELETE", f"/objects/{object_id}", response, [200, 204])
        
        # Verify object is deleted
        response = requests.get(f"{BASE_URL}/objects/{object_id}")
        assert_response_status("GET", f"/objects/{object_id}", response, 404)

def test_objects_head_operations():
    """Test HEAD operations for objects"""
    print_section("OBJECTS HEAD OPERATIONS")
    
    if not test_data.get("object_ids"):
        print("❌ No object_ids available for HEAD test")
        return
    
    # Test HEAD for each object
    for i, object_id in enumerate(test_data["object_ids"], 1):
        print_subsection(f"HEAD Object {i}")
        
        response = requests.head(f"{BASE_URL}/objects/{object_id}")
        assert_response_status("HEAD", f"/objects/{object_id}", response, 200)
        
        # Check headers
        print(f"   Object: {object_id}")
        print(f"   Content-Type: {response.headers.get('Content-Type', 'N/A')}")
        print(f"   Content-Length: {response.headers.get('Content-Length', 'N/A')}")
        print(f"   Last-Modified: {response.headers.get('Last-Modified', 'N/A')}")

def test_objects_error_cases():
    """Test object error cases"""
    print_section("OBJECTS ERROR CASES")
    
    # Test with non-existent object
    print_subsection("Non-existent Object")
    response = requests.get(f"{BASE_URL}/objects/nonexistent-object-id")
    assert_response_status("GET", "/objects/nonexistent-object-id", response, 404)
    
    # Test HEAD with non-existent object
    print_subsection("HEAD Non-existent Object")
    response = requests.head(f"{BASE_URL}/objects/nonexistent-object-id")
    assert_response_status("HEAD", "/objects/nonexistent-object-id", response, 404)
    
    # Test DELETE with non-existent object
    print_subsection("DELETE Non-existent Object")
    response = requests.delete(f"{BASE_URL}/objects/nonexistent-object-id")
    assert_response_status("DELETE", "/objects/nonexistent-object-id", response, 404)

def test_objects_upload_workflow():
    """Test complete object upload workflow"""
    print_section("OBJECTS UPLOAD WORKFLOW")
    
    # Create source and flow
    test_data["source_id"] = create_test_source()
    test_data["flow_id"] = create_test_flow(test_data["source_id"])
    
    # Allocate storage
    print_subsection("ALLOCATE Storage for Upload")
    storage_request = {
        "limit": 1,
        "metadata": {
            "purpose": "upload_testing",
            "format": "video/H264",
            "content_type": "video/mp4"
        }
    }
    
    response = requests.post(f"{BASE_URL}/flows/{test_data['flow_id']}/storage", json=storage_request)
    storage_data = assert_response_success("POST", f"/flows/{test_data['flow_id']}/storage", response, 201)
    
    object_id = storage_data["media_objects"][0]["object_id"]
    test_data["object_ids"].append(object_id)
    
    print(f"   Allocated Object: {object_id}")
    print(f"   Storage Path: {storage_data['media_objects'][0].get('metadata', {}).get('storage_path', 'N/A')}")
    
    # Get object info to verify upload URL
    print_subsection("VERIFY Upload URL")
    response = requests.get(f"{BASE_URL}/objects/{object_id}")
    data = assert_response_success("GET", f"/objects/{object_id}", response, 200)
    
    if "put_url" in data and data["put_url"]:
        put_url_info = data["put_url"]
        print(f"   Upload URL: {put_url_info.get('url', 'N/A')[:50]}...")
        print(f"   Upload Method: {put_url_info.get('method', 'N/A')}")
        
        # Test URL accessibility
        if "url" in put_url_info:
            try:
                head_response = requests.head(put_url_info["url"], timeout=5)
                print(f"   Upload URL Status: {head_response.status_code}")
                if head_response.status_code == 200:
                    print("   ✅ Upload URL is accessible")
                else:
                    print("   ⚠️  Upload URL returned unexpected status")
            except Exception as e:
                print(f"   ⚠️  Upload URL test failed: {e}")
    else:
        print("   ❌ No upload URL available")

def test_objects_content_validation():
    """Test object content validation"""
    print_section("OBJECTS CONTENT VALIDATION")
    
    if not test_data.get("object_ids"):
        print("❌ No object_ids available for content validation test")
        return
    
    # Test content validation for each object
    for i, object_id in enumerate(test_data["object_ids"], 1):
        print_subsection(f"Content Validation for Object {i}")
        
        response = requests.get(f"{BASE_URL}/objects/{object_id}")
        data = assert_response_success("GET", f"/objects/{object_id}", response, 200)
        
        print(f"   Object: {object_id}")
        
        # Check content type
        if "metadata" in data and "content_type" in data["metadata"]:
            content_type = data["metadata"]["content_type"]
            print(f"   Content Type: {content_type}")
            
            # Validate content type format
            if "/" in content_type:
                print("   ✅ Content type format is valid")
            else:
                print("   ⚠️  Content type format might be invalid")
        
        # Check content length
        if "metadata" in data and "content_length" in data["metadata"]:
            content_length = data["metadata"]["content_length"]
            print(f"   Content Length: {content_length}")
            
            if isinstance(content_length, int) and content_length >= 0:
                print("   ✅ Content length is valid")
            else:
                print("   ⚠️  Content length might be invalid")
        
        # Check checksum if available
        if "metadata" in data and "checksum" in data["metadata"]:
            checksum = data["metadata"]["checksum"]
            print(f"   Checksum: {checksum}")
            print("   ✅ Checksum available for integrity validation")

def run_all_objects_tests():
    """Run all objects tests"""
    print("🚀 Starting Objects Endpoint Tests")
    print(f"🔗 Base URL: {BASE_URL}")
    print(f"⏰ Start Time: {datetime.now().isoformat()}")
    
    try:
        test_objects_crud()
        test_objects_upload_urls()
        test_objects_metadata()
        test_objects_upload_workflow()
        test_objects_content_validation()
        test_objects_deletion()
        test_objects_head_operations()
        test_objects_error_cases()
        
        print_section("OBJECTS TESTS SUMMARY")
        print("✅ All objects endpoint tests completed successfully")
        
    except Exception as e:
        print(f"❌ Objects tests failed: {e}")
        raise
    finally:
        cleanup_test_data()

if __name__ == "__main__":
    run_all_objects_tests()
