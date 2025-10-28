#!/usr/bin/env python3
"""
Test S3 Object Upload Workflow

This script tests the complete S3 upload workflow:
1. Create a source
2. Create a flow linked to the source
3. Generate presigned URL for S3 upload
4. Upload an object to S3 via the presigned URL
5. Create a segment referencing the uploaded object
"""

import requests
import json
import uuid
from pathlib import Path

# Configuration
API_BASE_URL = "http://localhost:8000"
USERNAME = "admin"
PASSWORD = "vastdata"

# Get auth token
def login():
    """Login and get JWT token"""
    response = requests.post(
        f"{API_BASE_URL}/auth/login",
        json={"username": USERNAME, "password": PASSWORD}
    )
    response.raise_for_status()
    return response.json()["access_token"]

def get_headers(token):
    """Get authorization headers"""
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

def create_source(token):
    """Create a test source"""
    source_id = str(uuid.uuid4())
    source_data = {
        "id": source_id,
        "format": "urn:x-nmos:format:video",
        "label": "Test Source",
        "description": "Test source for S3 upload validation",
        "created_by": "test",
        "updated_by": "test"
    }
    
    response = requests.post(
        f"{API_BASE_URL}/sources",
        json=source_data,
        headers=get_headers(token)
    )
    response.raise_for_status()
    print(f"✅ Created source: {source_id}")
    return response.json()

def create_flow(token, source_id):
    """Create a test flow linked to source"""
    flow_id = str(uuid.uuid4())
    # Video flow with required fields
    flow_data = {
        "id": flow_id,
        "source_id": source_id,
        "generation": 1,
        "format": "urn:x-nmos:format:video",
        "label": "Test Flow",
        "description": "Test flow for S3 upload validation",
        "codec": "video/h264",
        "essence_parameters": {
            "frame_width": 1920,
            "frame_height": 1080,
            "frame_rate": {
                "numerator": 25,
                "denominator": 1
            },
            "vfr": False
        }
    }
    
    response = requests.post(
        f"{API_BASE_URL}/flows",
        json=flow_data,
        headers=get_headers(token)
    )
    if response.status_code == 422:
        print(f"❌ Validation error: {response.json()}")
    response.raise_for_status()
    print(f"✅ Created flow: {flow_id}")
    return response.json()

def get_presigned_url(token, flow_id, label="test-object"):
    """Get presigned URL for S3 upload"""
    storage_data = {
        "label": label,
        "limit": 1  # Request only 1 presigned URL for testing
    }
    
    response = requests.post(
        f"{API_BASE_URL}/flows/{flow_id}/storage",
        json=storage_data,
        headers=get_headers(token)
    )
    response.raise_for_status()
    result = response.json()
    
    # Extract presigned URL from response
    # Response format: {'pre': None, 'media_objects': [{'object_id': '...', 'put_url': {'url': '...'}}]}
    if "media_objects" in result and len(result["media_objects"]) > 0:
        media_obj = result["media_objects"][0]
        object_id = media_obj["object_id"]
        presigned_url = media_obj["put_url"]["url"]
        print(f"✅ Got presigned URL: {presigned_url[:50]}...")
        return presigned_url, object_id
    else:
        print(f"❌ No media_objects in response: {result}")
        return None, None

def upload_to_s3(presigned_url, test_data):
    """Upload data to S3 using presigned URL
    Note: Do NOT add headers unless they were included in the presigned URL signature
    """
    response = requests.put(
        presigned_url,
        data=test_data
    )
    response.raise_for_status()
    print(f"✅ Uploaded to S3: status {response.status_code}")
    return True

def create_segment(token, flow_id, object_id):
    """Create a segment for the flow"""
    # Use TAMS timerange format with TimeRange object
    segment_data = {
        "object_id": object_id,
        "timerange": {
            "value": "[0:0_10:0)"  # TAMS timerange format: [start_end) where times are seconds:nanoseconds
        }
    }
    
    response = requests.post(
        f"{API_BASE_URL}/flows/{flow_id}/segments",
        json=segment_data,
        headers=get_headers(token)
    )
    response.raise_for_status()
    print(f"✅ Created segment with object_id: {object_id}")
    return response.json()

def main():
    """Run the complete test workflow"""
    print("🧪 Testing S3 Object Upload Workflow\n")
    
    try:
        # 1. Login
        print("1. Logging in...")
        token = login()
        
        # 2. Create source
        print("\n2. Creating source...")
        source = create_source(token)
        source_id = source["id"]
        
        # 3. Create flow
        print("\n3. Creating flow...")
        flow = create_flow(token, source_id)
        flow_id = flow["id"]
        
        # 4. Get presigned URL
        print("\n4. Getting presigned URL for S3 upload...")
        presigned_url, object_id = get_presigned_url(token, flow_id)
        
        if not presigned_url:
            print("❌ Failed to get presigned URL")
            return
        
        # 5. Upload test data
        print("\n5. Uploading test data to S3...")
        test_data = b"This is test content for S3 upload validation"
        upload_to_s3(presigned_url, test_data)
        
        # 6. Create segment
        print("\n6. Creating segment...")
        segment = create_segment(token, flow_id, object_id)
        
        print("\n✅ S3 upload workflow test completed successfully!")
        print(f"\nSummary:")
        print(f"  Source ID: {source_id}")
        print(f"  Flow ID: {flow_id}")
        print(f"  Object ID: {object_id}")
        print(f"  Segment ID: {segment.get('id', 'N/A')}")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

