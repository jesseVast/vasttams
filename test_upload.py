#!/usr/bin/env python3
"""
Test script to upload a file to TAMS flow storage using presigned URLs
"""

import requests
import json
import os

def test_tams_upload():
    """Test the complete TAMS workflow: storage allocation -> upload -> segment registration"""
    
    # Step 1: Allocate storage for the flow
    flow_id = "d2e3f4a5-6b7c-4d8e-9f0a-1b2c3d4e5f6a"
    storage_url = f"http://localhost:8000/flows/{flow_id}/storage"
    
    print(f"🔧 Allocating storage for flow: {flow_id}")
    
    response = requests.post(
        storage_url,
        json={"limit": 1},
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code != 201:
        print(f"❌ Failed to allocate storage: {response.status_code}")
        print(f"Response: {response.text}")
        return None
    
    storage_data = response.json()
    print(f"✅ Storage allocated successfully")
    print(f"   Object ID: {storage_data['media_objects'][0]['object_id']}")
    print(f"   Storage Path: {storage_data['media_objects'][0]['metadata']['storage_path']}")
    
    # Step 2: Upload media file using presigned URL
    media_object = storage_data['media_objects'][0]
    object_id = media_object['object_id']
    put_url = media_object['put_url']['url']
    
    print(f"\n📤 Uploading media file to object: {object_id}")
    
    # Create a test file with some content
    test_file_path = "test_media.dat"
    test_content = b"This is test media content for TAMS workflow - " + b"x" * 1000  # 1KB + content
    
    with open(test_file_path, "wb") as f:
        f.write(test_content)
    
    print(f"   Created test file: {test_file_path} ({len(test_content)} bytes)")
    
    # Upload using presigned URL
    try:
        with open(test_file_path, "rb") as f:
            upload_response = requests.put(
                put_url,
                data=f
                # No extra headers - let the presigned URL handle everything
            )
        
        if upload_response.status_code == 200:
            print(f"✅ Media upload successful!")
            print(f"   Uploaded {len(test_content)} bytes")
        else:
            print(f"❌ Media upload failed: {upload_response.status_code}")
            print(f"   Response: {upload_response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Upload error: {e}")
        return None
    finally:
        # Clean up test file
        if os.path.exists(test_file_path):
            os.remove(test_file_path)
            print(f"   Cleaned up test file: {test_file_path}")
    
    # Step 3: Register flow segment with the uploaded object (metadata only)
    print(f"\n📝 Registering flow segment with uploaded object")
    
    segment_url = f"http://localhost:8000/flows/{flow_id}/segments"
    
    segment_data = {
        "object_id": object_id,
        "timerange": "[0:0_30:0]",
        "ts_offset": "0:0",
        "storage_path": media_object['metadata']['storage_path']  # Use the storage path from allocation
    }
    
    # Register segment metadata only (no file upload - file already uploaded to S3)
    files = {
        'segment_data': (None, json.dumps(segment_data), 'application/json')
    }
    
    try:
        segment_response = requests.post(segment_url, files=files)
        
        if segment_response.status_code == 201:
            print(f"✅ Flow segment registered successfully!")
            segment_info = segment_response.json()
            print(f"   Segment ID: {segment_info.get('id', 'N/A')}")
            print(f"   Object ID: {segment_info.get('object_id', 'N/A')}")
        else:
            print(f"❌ Failed to register segment: {segment_response.status_code}")
            print(f"   Response: {segment_response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Segment registration error: {e}")
        return None
    
    print(f"\n🎉 Complete TAMS workflow test successful!")
    print(f"   Source → Flow → Storage Allocation → Media Upload → Segment Registration")
    
    return {
        "flow_id": flow_id,
        "object_id": object_id,
        "storage_path": media_object['metadata']['storage_path']
    }

if __name__ == "__main__":
    print("🚀 Testing TAMS Complete Workflow")
    print("=" * 50)
    
    result = test_tams_upload()
    
    if result:
        print(f"\n📊 Test Summary:")
        print(f"   Flow ID: {result['flow_id']}")
        print(f"   Object ID: {result['object_id']}")
        print(f"   Storage Path: {result['storage_path']}")
    else:
        print(f"\n💥 Test failed!")
        exit(1)
