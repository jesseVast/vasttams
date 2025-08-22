#!/usr/bin/env python3
"""
Comprehensive CRUD testing for all TAMS API endpoints
Tests the complete functionality after TAMS storage path implementation
"""

import requests
import json
import uuid
from datetime import datetime
import time

# Base URL for the API
BASE_URL = "http://localhost:8000"

# Test data storage
test_data = {
    "source_id": None,
    "flow_id": None,
    "object_ids": [],
    "segment_ids": [],
    "collection_ids": []
}

def generate_uuid():
    """Generate a UUID4 string"""
    return str(uuid.uuid4())

def print_section(title):
    """Print a formatted section header"""
    print(f"\n{'='*60}")
    print(f"🧪 {title}")
    print('='*60)

def print_subsection(title):
    """Print a formatted subsection header"""
    print(f"\n--- {title} ---")

def print_result(operation, endpoint, status_code, data=None, error=None):
    """Print formatted test result"""
    status_emoji = "✅" if 200 <= status_code < 300 else "❌"
    print(f"{status_emoji} {operation} {endpoint}: {status_code}")
    
    if error:
        print(f"   Error: {error}")
    elif data and isinstance(data, dict):
        if 'id' in data:
            print(f"   ID: {data['id']}")
        if 'object_id' in data:
            print(f"   Object ID: {data['object_id']}")
        if 'storage_path' in data:
            print(f"   Storage Path: {data['storage_path']}")
        if 'get_urls' in data and data['get_urls']:
            print(f"   get_urls: {len(data['get_urls'])} URLs generated")
    elif data and isinstance(data, list):
        print(f"   Count: {len(data)} items")

def test_health():
    """Test health endpoint"""
    print_section("HEALTH CHECK")
    
    try:
        response = requests.get(f"{BASE_URL}/health")
        data = response.json()
        print_result("GET", "/health", response.status_code, data)
        return response.status_code == 200
    except Exception as e:
        print_result("GET", "/health", 0, error=str(e))
        return False

def test_root_endpoints():
    """Test TAMS root endpoints"""
    print_section("TAMS ROOT ENDPOINTS")
    
    # GET /
    print_subsection("GET Root Endpoints")
    try:
        response = requests.get(f"{BASE_URL}/")
        data = response.json()
        print_result("GET", "/", response.status_code, data)
    except Exception as e:
        print_result("GET", "/", 0, error=str(e))
    
    # HEAD /
    print_subsection("HEAD Root Endpoints")
    try:
        response = requests.head(f"{BASE_URL}/")
        print_result("HEAD", "/", response.status_code)
    except Exception as e:
        print_result("HEAD", "/", 0, error=str(e))

def test_service_endpoints():
    """Test TAMS service endpoints"""
    print_section("TAMS SERVICE ENDPOINTS")
    
    # GET /service
    print_subsection("GET Service Information")
    try:
        response = requests.get(f"{BASE_URL}/service")
        data = response.json()
        print_result("GET", "/service", response.status_code, data)
    except Exception as e:
        print_result("GET", "/service", 0, error=str(e))
    
    # HEAD /service
    print_subsection("HEAD Service Information")
    try:
        response = requests.head(f"{BASE_URL}/service")
        print_result("HEAD", "/service", response.status_code)
    except Exception as e:
        print_result("HEAD", "/service", 0, error=str(e))
    
    # GET /service/storage-backends
    print_subsection("GET Storage Backends")
    try:
        response = requests.get(f"{BASE_URL}/service/storage-backends")
        data = response.json()
        print_result("GET", "/service/storage-backends", response.status_code, data)
    except Exception as e:
        print_result("GET", "/service/storage-backends", 0, error=str(e))
    
    # HEAD /service/storage-backends
    print_subsection("HEAD Storage Backends")
    try:
        response = requests.head(f"{BASE_URL}/service/storage-backends")
        print_result("HEAD", "/service/storage-backends", response.status_code)
    except Exception as e:
        print_result("HEAD", "/service/storage-backends", 0, error=str(e))

def test_sources_crud():
    """Test Sources CRUD operations"""
    print_section("SOURCES CRUD")
    
    # CREATE - POST /sources
    print_subsection("CREATE Source")
    source_data = {
        "id": generate_uuid(),
        "label": "Test Video Source",
        "description": "Test source for CRUD testing",
        "format": "urn:x-nmos:format:video",
        "channels": [
            {
                "label": "Test Channel",
                "description": "Test video channel"
            }
        ]
    }
    
    try:
        response = requests.post(f"{BASE_URL}/sources", json=source_data)
        if response.status_code == 201:
            data = response.json()
            test_data["source_id"] = data["id"]
            print_result("POST", "/sources", response.status_code, data)
        else:
            print_result("POST", "/sources", response.status_code, error=response.text)
    except Exception as e:
        print_result("POST", "/sources", 0, error=str(e))
    
    # READ - GET /sources
    print_subsection("READ Sources List")
    try:
        response = requests.get(f"{BASE_URL}/sources")
        data = response.json()
        print_result("GET", "/sources", response.status_code, data.get("data", []))
    except Exception as e:
        print_result("GET", "/sources", 0, error=str(e))
    
    # READ - GET /sources/{source_id}
    if test_data["source_id"]:
        print_subsection("READ Specific Source")
        try:
            response = requests.get(f"{BASE_URL}/sources/{test_data['source_id']}")
            data = response.json()
            print_result("GET", f"/sources/{test_data['source_id']}", response.status_code, data)
        except Exception as e:
            print_result("GET", f"/sources/{test_data['source_id']}", 0, error=str(e))

def test_source_tags():
    """Test Source Tags operations"""
    print_section("SOURCE TAGS")
    
    if not test_data["source_id"]:
        print("❌ No source_id available for tags test")
        return
    
    # GET /sources/{source_id}/tags
    print_subsection("GET Source Tags")
    try:
        response = requests.get(f"{BASE_URL}/sources/{test_data['source_id']}/tags")
        data = response.json()
        print_result("GET", f"/sources/{test_data['source_id']}/tags", response.status_code, data)
    except Exception as e:
        print_result("GET", f"/sources/{test_data['source_id']}/tags", 0, error=str(e))
    
    # POST /sources/{source_id}/tags
    print_subsection("POST Source Tags")
    tags_data = {"test_tag": "test_value", "environment": "testing"}
    try:
        response = requests.post(f"{BASE_URL}/sources/{test_data['source_id']}/tags", json=tags_data)
        print_result("POST", f"/sources/{test_data['source_id']}/tags", response.status_code)
    except Exception as e:
        print_result("POST", f"/sources/{test_data['source_id']}/tags", 0, error=str(e))
    
    # GET specific tag
    print_subsection("GET Specific Source Tag")
    try:
        response = requests.get(f"{BASE_URL}/sources/{test_data['source_id']}/tags/test_tag")
        data = response.json()
        print_result("GET", f"/sources/{test_data['source_id']}/tags/test_tag", response.status_code, data)
    except Exception as e:
        print_result("GET", f"/sources/{test_data['source_id']}/tags/test_tag", 0, error=str(e))

def test_source_properties():
    """Test Source Properties operations"""
    print_section("SOURCE PROPERTIES")
    
    if not test_data["source_id"]:
        print("❌ No source_id available for properties test")
        return
    
    # Test description
    print_subsection("Source Description")
    try:
        response = requests.get(f"{BASE_URL}/sources/{test_data['source_id']}/description")
        print_result("GET", f"/sources/{test_data['source_id']}/description", response.status_code)
    except Exception as e:
        print_result("GET", f"/sources/{test_data['source_id']}/description", 0, error=str(e))
    
    # Test label
    print_subsection("Source Label")
    try:
        response = requests.get(f"{BASE_URL}/sources/{test_data['source_id']}/label")
        print_result("GET", f"/sources/{test_data['source_id']}/label", response.status_code)
    except Exception as e:
        print_result("GET", f"/sources/{test_data['source_id']}/label", 0, error=str(e))

def test_flows_crud():
    """Test Flows CRUD operations"""
    print_section("FLOWS CRUD")
    
    # CREATE - POST /flows
    print_subsection("CREATE Flow")
    flow_data = {
        "id": generate_uuid(),
        "source_id": test_data["source_id"] or generate_uuid(),
        "label": "Test Video Flow",
        "description": "Test flow for CRUD testing",
        "format": "urn:x-nmos:format:video",
        "codec": "video/H264",
        "frame_rate": {"numerator": 25, "denominator": 1},
        "frame_width": 1920,
        "frame_height": 1080,
        "sample_rate": 48000,
        "channels": 2,
        "bit_rate": 5000000
    }
    
    try:
        response = requests.post(f"{BASE_URL}/flows", json=flow_data)
        if response.status_code == 201:
            data = response.json()
            test_data["flow_id"] = data["id"]
            print_result("POST", "/flows", response.status_code, data)
        else:
            print_result("POST", "/flows", response.status_code, error=response.text)
    except Exception as e:
        print_result("POST", "/flows", 0, error=str(e))
    
    # READ - GET /flows
    print_subsection("READ Flows List")
    try:
        response = requests.get(f"{BASE_URL}/flows")
        data = response.json()
        print_result("GET", "/flows", response.status_code, data.get("data", []))
    except Exception as e:
        print_result("GET", "/flows", 0, error=str(e))
    
    # READ - GET /flows/{flow_id}
    if test_data["flow_id"]:
        print_subsection("READ Specific Flow")
        try:
            response = requests.get(f"{BASE_URL}/flows/{test_data['flow_id']}")
            data = response.json()
            print_result("GET", f"/flows/{test_data['flow_id']}", response.status_code, data)
        except Exception as e:
            print_result("GET", f"/flows/{test_data['flow_id']}", 0, error=str(e))

def test_flow_properties():
    """Test Flow Properties operations"""
    print_section("FLOW PROPERTIES")
    
    if not test_data["flow_id"]:
        print("❌ No flow_id available for properties test")
        return
    
    # Test read-only status
    print_subsection("Flow Read-Only Status")
    try:
        response = requests.get(f"{BASE_URL}/flows/{test_data['flow_id']}/read_only")
        print_result("GET", f"/flows/{test_data['flow_id']}/read_only", response.status_code)
    except Exception as e:
        print_result("GET", f"/flows/{test_data['flow_id']}/read_only", 0, error=str(e))
    
    # Test max bit rate
    print_subsection("Flow Max Bit Rate")
    try:
        response = requests.get(f"{BASE_URL}/flows/{test_data['flow_id']}/max_bit_rate")
        print_result("GET", f"/flows/{test_data['flow_id']}/max_bit_rate", response.status_code)
    except Exception as e:
        print_result("GET", f"/flows/{test_data['flow_id']}/max_bit_rate", 0, error=str(e))
    
    # Test average bit rate
    print_subsection("Flow Average Bit Rate")
    try:
        response = requests.get(f"{BASE_URL}/flows/{test_data['flow_id']}/avg_bit_rate")
        print_result("GET", f"/flows/{test_data['flow_id']}/avg_bit_rate", response.status_code)
    except Exception as e:
        print_result("GET", f"/flows/{test_data['flow_id']}/avg_bit_rate", 0, error=str(e))

def test_flow_collection():
    """Test Flow Collection operations"""
    print_section("FLOW COLLECTION")
    
    if not test_data["flow_id"]:
        print("❌ No flow_id available for collection test")
        return
    
    # GET /flows/{flow_id}/flow_collection
    print_subsection("GET Flow Collection")
    try:
        response = requests.get(f"{BASE_URL}/flows/{test_data['flow_id']}/flow_collection")
        print_result("GET", f"/flows/{test_data['flow_id']}/flow_collection", response.status_code)
    except Exception as e:
        print_result("GET", f"/flows/{test_data['flow_id']}/flow_collection", 0, error=str(e))
    
    # PUT /flows/{flow_id}/flow_collection
    print_subsection("PUT Flow Collection")
    collection_data = {"collection_id": generate_uuid()}
    try:
        response = requests.put(f"{BASE_URL}/flows/{test_data['flow_id']}/flow_collection", json=collection_data)
        print_result("PUT", f"/flows/{test_data['flow_id']}/flow_collection", response.status_code)
    except Exception as e:
        print_result("PUT", f"/flows/{test_data['flow_id']}/flow_collection", 0, error=str(e))

def test_storage_allocation():
    """Test Flow Storage Allocation"""
    print_section("FLOW STORAGE ALLOCATION")
    
    if not test_data["flow_id"]:
        print("❌ No flow_id available for storage allocation test")
        return
    
    # CREATE - POST /flows/{flow_id}/storage
    print_subsection("ALLOCATE Storage")
    storage_request = {
        "object_ids": [generate_uuid(), generate_uuid()]
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/flows/{test_data['flow_id']}/storage",
            json=storage_request
        )
        if response.status_code == 201:
            data = response.json()
            test_data["object_ids"] = [obj["object_id"] for obj in data["media_objects"]]
            print_result("POST", f"/flows/{test_data['flow_id']}/storage", response.status_code)
            print(f"   📁 Storage Objects: {len(data['media_objects'])}")
            for i, obj in enumerate(data["media_objects"]):
                print(f"      Object {i+1}: {obj['object_id']}")
                print(f"      Storage Path: {obj['metadata']['storage_path']}")
                print(f"      Presigned URL: {obj['put_url']['url'][:80]}...")
        else:
            print_result("POST", f"/flows/{test_data['flow_id']}/storage", response.status_code, error=response.text)
    except Exception as e:
        print_result("POST", f"/flows/{test_data['flow_id']}/storage", 0, error=str(e))

def test_segments_crud():
    """Test Flow Segments CRUD operations"""
    print_section("FLOW SEGMENTS CRUD")
    
    if not test_data["flow_id"]:
        print("❌ No flow_id available for segments test")
        return
    
    # CREATE - POST /flows/{flow_id}/segments (metadata only)
    print_subsection("CREATE Segment (Metadata Only)")
    if test_data["object_ids"]:
        object_id = test_data["object_ids"][0]
        # Get current date for TAMS path
        now = datetime.now()
        storage_path = f"tams/{now.year:04d}/{now.month:02d}/{now.day:02d}/{object_id}"
        
        segment_data = {
            "object_id": object_id,
            "timerange": "[0:0_30:0]",
            "ts_offset": "0:0",
            "storage_path": storage_path
        }
        
        try:
            files = {
                'segment_data': (None, json.dumps(segment_data), 'application/json')
            }
            response = requests.post(
                f"{BASE_URL}/flows/{test_data['flow_id']}/segments",
                files=files
            )
            if response.status_code == 201:
                data = response.json()
                test_data["segment_ids"].append(data["object_id"])
                print_result("POST", f"/flows/{test_data['flow_id']}/segments", response.status_code, data)
            else:
                print_result("POST", f"/flows/{test_data['flow_id']}/segments", response.status_code, error=response.text)
        except Exception as e:
            print_result("POST", f"/flows/{test_data['flow_id']}/segments", 0, error=str(e))
    
    # READ - GET /flows/{flow_id}/segments
    print_subsection("READ Segments List")
    try:
        response = requests.get(f"{BASE_URL}/flows/{test_data['flow_id']}/segments")
        data = response.json()
        print_result("GET", f"/flows/{test_data['flow_id']}/segments", response.status_code, data)
        
        # Check if get_urls are generated dynamically
        if data and len(data) > 0:
            segment = data[0]
            if segment.get("get_urls"):
                print(f"   🔗 Dynamic get_urls: {len(segment['get_urls'])} URLs generated")
                for i, get_url in enumerate(segment["get_urls"]):
                    print(f"      URL {i+1}: {get_url['url'][:80]}...")
            else:
                print("   ⚠️  No get_urls generated")
    except Exception as e:
        print_result("GET", f"/flows/{test_data['flow_id']}/segments", 0, error=str(e))

def test_objects_endpoint():
    """Test Objects endpoint"""
    print_section("OBJECTS ENDPOINT")
    
    if not test_data["object_ids"]:
        print("❌ No object_ids available for objects test")
        return
    
    # GET /objects/{object_id}
    print_subsection("GET Object Information")
    object_id = test_data["object_ids"][0]
    try:
        response = requests.get(f"{BASE_URL}/objects/{object_id}")
        print_result("GET", f"/objects/{object_id}", response.status_code)
    except Exception as e:
        print_result("GET", f"/objects/{object_id}", 0, error=str(e))
    
    # HEAD /objects/{object_id}
    print_subsection("HEAD Object Information")
    try:
        response = requests.head(f"{BASE_URL}/objects/{object_id}")
        print_result("HEAD", f"/objects/{object_id}", response.status_code)
    except Exception as e:
        print_result("HEAD", f"/objects/{object_id}", 0, error=str(e))

def test_webhooks():
    """Test Webhooks endpoint"""
    print_section("WEBHOOKS")
    
    # GET /service/webhooks
    print_subsection("GET Webhooks")
    try:
        response = requests.get(f"{BASE_URL}/service/webhooks")
        data = response.json()
        print_result("GET", "/service/webhooks", response.status_code, data)
    except Exception as e:
        print_result("GET", "/service/webhooks", 0, error=str(e))

def test_deletion_requests():
    """Test Deletion Requests endpoint"""
    print_section("DELETION REQUESTS")
    
    # GET /flow-delete-requests
    print_subsection("GET Deletion Requests")
    try:
        response = requests.get(f"{BASE_URL}/flow-delete-requests")
        data = response.json()
        print_result("GET", "/flow-delete-requests", response.status_code, data)
    except Exception as e:
        print_result("GET", "/flow-delete-requests", 0, error=str(e))

def main():
    """Run comprehensive CRUD testing"""
    print("🚀 Starting Comprehensive TAMS API CRUD Testing")
    print(f"🔗 Base URL: {BASE_URL}")
    print(f"⏰ Start Time: {datetime.now().isoformat()}")
    
    # Test in logical order
    if not test_health():
        print("❌ Health check failed. Server may not be running.")
        return
    
    test_root_endpoints()
    test_service_endpoints()
    test_sources_crud()
    test_source_tags()
    test_source_properties()
    test_flows_crud()
    test_flow_properties()
    test_flow_collection()
    test_storage_allocation()
    test_segments_crud()
    test_objects_endpoint()
    test_webhooks()
    test_deletion_requests()
    
    # Summary
    print_section("TEST SUMMARY")
    print(f"✅ TAMS API CRUD testing completed")
    print(f"⏰ End Time: {datetime.now().isoformat()}")
    print(f"📊 Test Data Generated:")
    print(f"   Source ID: {test_data['source_id']}")
    print(f"   Flow ID: {test_data['flow_id']}")
    print(f"   Object IDs: {len(test_data['object_ids'])} objects")
    print(f"   Segment IDs: {len(test_data['segment_ids'])} segments")

if __name__ == "__main__":
    main()
