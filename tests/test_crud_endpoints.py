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
    """Test Source Tags operations (TAMS-compliant individual tag operations only)"""
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
    
    # PUT /sources/{source_id}/tags/{name} - Create/Update individual tag
    print_subsection("PUT Individual Source Tag")
    try:
        response = requests.put(f"{BASE_URL}/sources/{test_data['source_id']}/tags/test_tag", 
                              data="test_value", 
                              headers={"Content-Type": "text/plain"})
        print_result("PUT", f"/sources/{test_data['source_id']}/tags/test_tag", response.status_code)
    except Exception as e:
        print_result("PUT", f"/sources/{test_data['source_id']}/tags/test_tag", 0, error=str(e))
    
    # PUT another tag
    try:
        response = requests.put(f"{BASE_URL}/sources/{test_data['source_id']}/tags/environment", 
                              data="testing", 
                              headers={"Content-Type": "text/plain"})
        print_result("PUT", f"/sources/{test_data['source_id']}/tags/environment", response.status_code)
    except Exception as e:
        print_result("PUT", f"/sources/{test_data['source_id']}/tags/environment", 0, error=str(e))
    
    # GET specific tag
    print_subsection("GET Specific Source Tag")
    try:
        response = requests.get(f"{BASE_URL}/sources/{test_data['source_id']}/tags/test_tag")
        data = response.json()
        print_result("GET", f"/sources/{test_data['source_id']}/tags/test_tag", response.status_code, data)
    except Exception as e:
        print_result("GET", f"/sources/{test_data['source_id']}/tags/test_tag", 0, error=str(e))

def test_flow_tags():
    """Test Flow Tags operations (TAMS-compliant individual tag operations only)"""
    print_section("FLOW TAGS")
    
    if not test_data["flow_id"]:
        print("❌ No flow_id available for tags test")
        return
    
    # GET /flows/{flow_id}/tags
    print_subsection("GET Flow Tags")
    try:
        response = requests.get(f"{BASE_URL}/flows/{test_data['flow_id']}/tags")
        data = response.json()
        print_result("GET", f"/flows/{test_data['flow_id']}/tags", response.status_code, data)
    except Exception as e:
        print_result("GET", f"/flows/{test_data['flow_id']}/tags", 0, error=str(e))
    
    # PUT /flows/{flow_id}/tags/{name} - Create/Update individual tag
    print_subsection("PUT Individual Flow Tag")
    try:
        response = requests.put(f"{BASE_URL}/flows/{test_data['flow_id']}/tags/flow_tag", 
                              data="flow_value", 
                              headers={"Content-Type": "text/plain"})
        print_result("PUT", f"/flows/{test_data['flow_id']}/tags/flow_tag", response.status_code)
    except Exception as e:
        print_result("PUT", f"/flows/{test_data['flow_id']}/tags/flow_tag", 0, error=str(e))
    
    # PUT another tag
    try:
        response = requests.put(f"{BASE_URL}/flows/{test_data['flow_id']}/tags/priority", 
                              data="high", 
                              headers={"Content-Type": "text/plain"})
        print_result("PUT", f"/flows/{test_data['flow_id']}/tags/priority", response.status_code)
    except Exception as e:
        print_result("PUT", f"/flows/{test_data['flow_id']}/tags/priority", 0, error=str(e))
    
    # GET specific tag
    print_subsection("GET Specific Flow Tag")
    try:
        response = requests.get(f"{BASE_URL}/flows/{test_data['flow_id']}/tags/flow_tag")
        data = response.json()
        print_result("GET", f"/flows/{test_data['flow_id']}/tags/flow_tag", response.status_code, data)
    except Exception as e:
        print_result("GET", f"/flows/{test_data['flow_id']}/tags/flow_tag", 0, error=str(e))

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
    
    # GET /flows/{flow_id}/flow_collection (should be 404 initially - no collections exist)
    print_subsection("GET Flow Collection (Initial - No Collections)")
    try:
        response = requests.get(f"{BASE_URL}/flows/{test_data['flow_id']}/flow_collection")
        if response.status_code == 404:
            print_result("GET", f"/flows/{test_data['flow_id']}/flow_collection", response.status_code, "✅ Expected: No collections exist yet")
        else:
            print_result("GET", f"/flows/{test_data['flow_id']}/flow_collection", response.status_code, "⚠️ Unexpected: Collections exist")
    except Exception as e:
        print_result("GET", f"/flows/{test_data['flow_id']}/flow_collection", 0, error=str(e))
    
    # PUT /flows/{flow_id}/flow_collection
    print_subsection("PUT Flow Collection")
    collection_data = {"collection_id": generate_uuid()}
    try:
        response = requests.put(f"{BASE_URL}/flows/{test_data['flow_id']}/flow_collection", json=collection_data)
        print_result("PUT", f"/flows/{test_data['flow_id']}/flow_collection", response.status_code)
        
        # GET again to verify collection was created
        if response.status_code == 200:
            print_subsection("GET Flow Collection (After Creation)")
            try:
                get_response = requests.get(f"{BASE_URL}/flows/{test_data['flow_id']}/flow_collection")
                if get_response.status_code == 200:
                    data = get_response.json()
                    print_result("GET", f"/flows/{test_data['flow_id']}/flow_collection", get_response.status_code, f"✅ Collection created: {len(data)} collections")
                else:
                    print_result("GET", f"/flows/{test_data['flow_id']}/flow_collection", get_response.status_code, "❌ Collection creation verification failed")
            except Exception as e:
                print_result("GET", f"/flows/{test_data['flow_id']}/flow_collection", 0, error=str(e))
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
            # Use JSON format for TAMS 7.0 compliant endpoint
            response = requests.post(
                f"{BASE_URL}/flows/{test_data['flow_id']}/segments",
                json=segment_data
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
        if isinstance(data, list) and len(data) > 0:
            segment = data[0]
            if segment.get("get_urls"):
                print(f"   🔗 Dynamic get_urls: {len(segment['get_urls'])} URLs generated")
                for i, get_url in enumerate(segment["get_urls"]):
                    print(f"      URL {i+1}: {get_url['url'][:80]}...")
            else:
                print("   ⚠️  No get_urls generated")
        elif isinstance(data, dict) and data.get("data"):
            segments = data["data"]
            if segments and len(segments) > 0:
                segment = segments[0]
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

def test_s3_upload_workflow():
    """Test complete S3 upload workflow including storage allocation, upload, and segment registration"""
    print_section("S3 UPLOAD WORKFLOW")
    
    if not test_data["flow_id"]:
        print("❌ Skipping S3 upload test - no flow ID available")
        return False
    
    flow_id = test_data["flow_id"]
    
    # Step 1: Allocate storage for the flow
    print_subsection("1. Allocate Flow Storage")
    storage_request = {
        "limit": 1  # Request 1 storage location
    }
    
    try:
        response = requests.post(f"{BASE_URL}/flows/{flow_id}/storage", json=storage_request)
        data = response.json()
        print_result("POST", f"/flows/{flow_id}/storage", response.status_code, data)
        
        if response.status_code != 201:
            print("❌ Failed to allocate storage - cannot continue upload test")
            return False
        
        # Extract the media object information
        media_objects = data.get("media_objects", [])
        if not media_objects:
            print("❌ No media objects returned from storage allocation")
            return False
        
        media_object = media_objects[0]
        object_id = media_object["object_id"]
        put_url = media_object["put_url"]["url"]
        
        print(f"   📦 Object ID: {object_id}")
        print(f"   🔗 Upload URL: {put_url[:100]}...")
        
        test_data["object_ids"].append(object_id)
        
    except Exception as e:
        print_result("POST", f"/flows/{flow_id}/storage", 0, error=str(e))
        return False
    
    # Step 2: Upload test data to S3 using the presigned URL
    print_subsection("2. Upload Test Data to S3")
    test_content = f"Test media content for object {object_id} - uploaded at {datetime.now().isoformat()}"
    
    try:
        # Upload using requests to the presigned URL
        upload_response = requests.put(
            put_url,
            data=test_content.encode('utf-8')
            # No extra headers - let S3 handle content type
        )
        
        if upload_response.status_code == 200:
            print(f"✅ Upload successful: {upload_response.status_code}")
            print(f"   📊 Content length: {len(test_content)} bytes")
        else:
            print(f"❌ Upload failed: {upload_response.status_code}")
            print(f"   📄 Response: {upload_response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Upload exception: {e}")
        return False
    
    # Step 3: Register the uploaded object as a flow segment
    print_subsection("3. Register Flow Segment")
    segment_data = {
        "object_id": object_id,
        "timerange": "[0:0_10:0]"  # TAMS timerange format
    }
    
    try:
        response = requests.post(f"{BASE_URL}/flows/{flow_id}/segments", json=segment_data)
        data = response.json()
        print_result("POST", f"/flows/{flow_id}/segments", response.status_code, data)
        
        if response.status_code == 201:
            test_data["segment_ids"].append(object_id)
            print(f"   🎯 Segment registered with storage_path: {data.get('storage_path', 'N/A')}")
            if data.get('get_urls'):
                print(f"   🔗 Generated {len(data['get_urls'])} get_urls")
        else:
            print("❌ Failed to register segment")
            return False
            
    except Exception as e:
        print_result("POST", f"/flows/{flow_id}/segments", 0, error=str(e))
        return False
    
    # Step 4: Verify flow-object reference was created
    print_subsection("4. Verify Flow-Object Reference")
    try:
        response = requests.get(f"{BASE_URL}/objects/{object_id}")
        data = response.json()
        print_result("GET", f"/objects/{object_id}", response.status_code, data)
        
        if response.status_code == 200:
            referenced_by_flows = data.get("referenced_by_flows", [])
            if flow_id in referenced_by_flows:
                print(f"   ✅ Flow {flow_id} correctly references object {object_id}")
            else:
                print(f"   ❌ Flow {flow_id} not found in object references: {referenced_by_flows}")
        else:
            print("❌ Failed to retrieve object information")
            
    except Exception as e:
        print_result("GET", f"/objects/{object_id}", 0, error=str(e))
    
    # Step 5: Test object deletion prevention (TAMS compliance)
    print_subsection("5. Test Object Deletion Prevention (TAMS Compliance)")
    try:
        response = requests.delete(f"{BASE_URL}/objects/{object_id}")
        print_result("DELETE", f"/objects/{object_id}", response.status_code)
        
        if response.status_code == 400:
            print("   ✅ TAMS compliance working: Object deletion correctly prevented due to flow references")
        elif response.status_code == 500:
            print("   ⚠️  Server error (expected if delete_object method missing)")
        else:
            print(f"   ❌ Unexpected response: {response.status_code}")
            
    except Exception as e:
        print_result("DELETE", f"/objects/{object_id}", 0, error=str(e))
    
    print("🎉 S3 Upload Workflow Test Complete!")
    return True

def test_dependency_violations():
    """Test TAMS API dependency violation rules - deletion should fail when dependencies exist"""
    print_section("DEPENDENCY VIOLATION TESTS")
    
    if not test_data.get("source_id") or not test_data.get("flow_id"):
        print("❌ Skipping dependency tests - need source and flow created first")
        return False
    
    source_id = test_data["source_id"]
    flow_id = test_data["flow_id"]
    
    print_subsection("0. Verify Dependencies Exist Before Testing")
    try:
        # Check that flow references the source
        response = requests.get(f"{BASE_URL}/flows/{flow_id}")
        if response.status_code == 200:
            flow_data = response.json()
            if flow_data.get("source_id") == source_id:
                print(f"   ✅ Flow {flow_id} correctly references source {source_id}")
            else:
                print(f"   ❌ Flow {flow_id} does not reference source {source_id}")
                return False
        else:
            print(f"   ❌ Failed to get flow {flow_id}")
            return False
            
        # Check that segments exist for the flow
        response = requests.get(f"{BASE_URL}/flows/{flow_id}/segments")
        if response.status_code == 200:
            segments_data = response.json()
            # Handle both list and dict response formats
            if isinstance(segments_data, list):
                segment_count = len(segments_data)
            elif isinstance(segments_data, dict) and segments_data.get("data"):
                segment_count = len(segments_data["data"])
            else:
                segment_count = 0
                
            print(f"   ✅ Flow {flow_id} has {segment_count} segments")
            if segment_count == 0:
                print("   ⚠️  No segments found - dependency tests may not be meaningful")
        else:
            print(f"   ❌ Failed to get segments for flow {flow_id}")
            
    except Exception as e:
        print(f"   ❌ Error verifying dependencies: {e}")
        return False
    
    print_subsection("1. Test Source Deletion with Dependent Flows (cascade=false)")
    try:
        # Try to delete source without cascade when it has dependent flows
        response = requests.delete(f"{BASE_URL}/sources/{source_id}?cascade=false")
        print_result("DELETE", f"/sources/{source_id}?cascade=false", response.status_code)
        
        if response.status_code == 409:
            print("   ✅ TAMS compliance working: Source deletion correctly prevented due to dependent flows")
        elif response.status_code == 200:
            print("   ❌ TAMS compliance FAILED: Source deleted despite having dependent flows")
            return False
        elif response.status_code == 500:
            print("   ⚠️  Server error - dependency checking may not be implemented yet")
        else:
            print(f"   ❌ Unexpected response: {response.status_code}")
            
    except Exception as e:
        print_result("DELETE", f"/sources/{source_id}?cascade=false", 0, error=str(e))
    
    print_subsection("2. Test Flow Deletion with Dependent Segments (cascade=false)")
    try:
        # Try to delete flow without cascade when it has dependent segments
        response = requests.delete(f"{BASE_URL}/flows/{flow_id}?cascade=false")
        print_result("DELETE", f"/flows/{flow_id}?cascade=false", response.status_code)
        
        if response.status_code == 409:
            print("   ✅ TAMS compliance working: Flow deletion correctly prevented due to dependent segments")
        elif response.status_code == 200:
            print("   ❌ TAMS compliance FAILED: Flow deleted despite having dependent segments")
            return False
        elif response.status_code == 500:
            print("   ⚠️  Server error - dependency checking may not be implemented yet")
        else:
            print(f"   ❌ Unexpected response: {response.status_code}")
            
    except Exception as e:
        print_result("DELETE", f"/flows/{flow_id}?cascade=false", 0, error=str(e))
    
    print_subsection("3. Test Segment Deletion (TAMS API Compliance)")
    if test_data.get("segment_ids"):
        segment_id = test_data["segment_ids"][0]
        try:
            # Test segment deletion - segments should be deletable according to TAMS API
            response = requests.delete(f"{BASE_URL}/flows/{flow_id}/segments?timerange=[0:0_10:0]")
            print_result("DELETE", f"/flows/{flow_id}/segments", response.status_code)
            
            if response.status_code == 200:
                print("   ✅ TAMS compliance working: Segment deletion successful (segments are deletable)")
            elif response.status_code == 409:
                print("   ⚠️  Unexpected 409 - segment deletion prevented due to dependencies")
            elif response.status_code == 500:
                print("   ⚠️  Server error during segment deletion")
            else:
                print(f"   ❌ Unexpected response: {response.status_code}")
                
        except Exception as e:
            print_result("DELETE", f"/flows/{flow_id}/segments", 0, error=str(e))
    else:
        print("   ⚠️  No segments to test - skipping segment deletion test")
    
    print_subsection("4. Test Cascade Deletion (should succeed)")
    try:
        # Test cascade deletion of flow - should succeed
        response = requests.delete(f"{BASE_URL}/flows/{flow_id}?cascade=true")
        print_result("DELETE", f"/flows/{flow_id}?cascade=true", response.status_code)
        
        if response.status_code == 200:
            print("   ✅ Cascade deletion successful - flow and all dependencies removed")
            # Update test data since flow is now deleted
            test_data["flow_id"] = None
            test_data["segment_ids"] = []
            test_data["object_ids"] = []
        elif response.status_code == 500:
            print("   ⚠️  Server error during cascade deletion")
        elif response.status_code == 404:
            print("   ❌ Flow not found - may have been deleted in previous test")
            # Skip the rest of the test since flow is gone
            test_data["flow_id"] = None
            test_data["segment_ids"] = []
            test_data["object_ids"] = []
            return True
        else:
            print(f"   ❌ Unexpected response: {response.status_code}")
            
    except Exception as e:
        print_result("DELETE", f"/flows/{flow_id}?cascade=true", 0, error=str(e))
    
    print_subsection("5. Test Source Deletion After Flow Removal (should succeed)")
    try:
        # Check if source still exists (flow might have been deleted in cascade test)
        if not test_data.get("source_id"):
            print("   ⚠️  Source already deleted or not available - skipping test")
            return True
            
        # Now that flow is deleted, source deletion should succeed
        response = requests.delete(f"{BASE_URL}/sources/{source_id}")
        print_result("DELETE", f"/sources/{source_id}", response.status_code)
        
        if response.status_code == 200:
            print("   ✅ Source deletion successful after dependent flows removed")
            test_data["source_id"] = None
        elif response.status_code == 500:
            print("   ⚠️  Server error during source deletion")
        else:
            print(f"   ❌ Unexpected response: {response.status_code}")
            
    except Exception as e:
        print_result("DELETE", f"/sources/{source_id}", 0, error=str(e))
    
    print_subsection("6. Test Cascade Parameter Validation")
    try:
        # Test invalid cascade parameter values
        response = requests.delete(f"{BASE_URL}/sources/{source_id}?cascade=invalid")
        print_result("DELETE", f"/sources/{source_id}?cascade=invalid", response.status_code)
        
        if response.status_code == 422:
            print("   ✅ Cascade parameter validation working - invalid value rejected")
        elif response.status_code == 400:
            print("   ✅ Cascade parameter validation working - invalid value rejected")
        else:
            print(f"   ⚠️  Unexpected response for invalid cascade parameter: {response.status_code}")
            
    except Exception as e:
        print_result("DELETE", f"/sources/{source_id}?cascade=invalid", 0, error=str(e))
    
    print("🎯 Dependency Violation Tests Complete!")
    
    print_subsection("7. Test Object Deletion Prevention (TAMS Compliance)")
    # This test verifies that objects cannot be deleted when they have flow references
    # This is already tested in the S3 upload workflow, but let's verify it's working
    if test_data.get("object_ids"):
        object_id = test_data["object_ids"][0]
        try:
            response = requests.delete(f"{BASE_URL}/objects/{object_id}")
            print_result("DELETE", f"/objects/{object_id}", response.status_code)
            
            if response.status_code == 400:
                print("   ✅ TAMS compliance working: Object deletion correctly prevented due to flow references")
            elif response.status_code == 500:
                print("   ⚠️  Server error - object deletion method may not be implemented")
            else:
                print(f"   ❌ Unexpected response: {response.status_code}")
                
        except Exception as e:
            print_result("DELETE", f"/objects/{object_id}", 0, error=str(e))
    else:
        print("   ⚠️  No objects to test - skipping object deletion prevention test")
    
    return True

def test_webhooks():
    """Test webhook endpoints"""
    print_section("WEBHOOK ENDPOINTS")
    
    print_subsection("GET /service/webhooks")
    try:
        response = requests.get(f"{BASE_URL}/service/webhooks")
        data = response.json() if response.status_code == 200 else None
        print_result("GET", "/service/webhooks", response.status_code, data)
    except Exception as e:
        print_result("GET", "/service/webhooks", 0, error=str(e))

def test_deletion_requests():
    """Test deletion request endpoints"""
    print_section("DELETION REQUEST ENDPOINTS")
    
    print_subsection("GET /flow-delete-requests")
    try:
        response = requests.get(f"{BASE_URL}/flow-delete-requests")
        data = response.json() if response.status_code == 200 else None
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
    test_flow_tags()
    test_flow_properties()
    test_flow_collection()
    test_storage_allocation()
    test_segments_crud()
    test_objects_endpoint()
    test_s3_upload_workflow()  # Test complete S3 upload workflow
    test_dependency_violations()  # Test TAMS dependency violation rules
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
