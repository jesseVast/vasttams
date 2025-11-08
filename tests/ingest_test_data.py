#!/usr/bin/env python3
"""
Test Data Ingestion Script

This script creates a complete test dataset:
- 2 sources
- 4 flows (3 video, 1 audio) - 2 flows share segments
- 10 objects (via S3 uploads)
- 10 segments (2 flows share some segments)

This validates the full workflow: source -> flow -> S3 upload -> segment creation
"""

import requests
import json
import uuid
from typing import Dict, List, Tuple
from datetime import datetime, timedelta

# Configuration
API_BASE_URL = "http://localhost:8000"
USERNAME = "admin"
PASSWORD = "vastdata"

# Track created resources for cleanup
created_resources = {
    "sources": [],
    "flows": [],
    "objects": [],
    "segments": []
}


def login():
    """Login and get JWT token"""
    response = requests.post(
        f"{API_BASE_URL}/auth/login",
        json={"username": USERNAME, "password": PASSWORD}
    )
    response.raise_for_status()
    return response.json()["access_token"]
def get_default_storage_id(token: str) -> str:
    """Fetch the default storage backend id (fallback to first backend)."""
    resp = requests.get(
        f"{API_BASE_URL}/service/storage-backends",
        headers=get_headers(token)
    )
    resp.raise_for_status()
    backends = resp.json()
    if isinstance(backends, dict) and "data" in backends:
        backends = backends["data"]
    if not backends:
        raise RuntimeError("No storage backends available")
    default_backend = next((b for b in backends if b.get("default_storage") is True), None)
    return (default_backend or backends[0]).get("id")



def get_headers(token):
    """Get authorization headers"""
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }


def create_source(token: str, source_num: int) -> Dict:
    """Create a test source"""
    source_id = str(uuid.uuid4())
    format_type = "urn:x-nmos:format:video" if source_num == 1 else "urn:x-nmos:format:video"
    
    source_data = {
        "id": source_id,
        "format": format_type,
        "label": f"Test Source {source_num}",
        "description": f"Test source {source_num} for data ingestion",
        "created_by": "test-script",
        "updated_by": "test-script"
    }
    
    response = requests.post(
        f"{API_BASE_URL}/sources",
        json=source_data,
        headers=get_headers(token)
    )
    response.raise_for_status()
    result = response.json()
    created_resources["sources"].append(source_id)
    print(f"✅ Created source {source_num}: {source_id[:8]}...")
    return result


def create_video_flow(token: str, source_id: str, flow_num: int, label: str = None) -> Dict:
    """Create a video flow"""
    flow_id = str(uuid.uuid4())
    flow_data = {
        "id": flow_id,
        "source_id": source_id,
        "generation": 1,
        "format": "urn:x-nmos:format:video",
        "label": label or f"Video Flow {flow_num}",
        "description": f"Test video flow {flow_num}",
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
    response.raise_for_status()
    result = response.json()
    created_resources["flows"].append(flow_id)
    print(f"✅ Created video flow {flow_num}: {flow_id[:8]}...")
    return result


def create_audio_flow(token: str, source_id: str, flow_num: int) -> Dict:
    """Create an audio flow"""
    flow_id = str(uuid.uuid4())
    flow_data = {
        "id": flow_id,
        "source_id": source_id,
        "generation": 1,
        "format": "urn:x-nmos:format:audio",
        "label": f"Audio Flow {flow_num}",
        "description": f"Test audio flow {flow_num}",
        "codec": "audio/aac",
        "essence_parameters": {
            "sample_rate": 48000,  # Integer, not an object
            "channels": 2
        }
    }
    
    response = requests.post(
        f"{API_BASE_URL}/flows",
        json=flow_data,
        headers=get_headers(token)
    )
    response.raise_for_status()
    result = response.json()
    created_resources["flows"].append(flow_id)
    print(f"✅ Created audio flow: {flow_id[:8]}...")
    return result


def get_presigned_url(token: str, flow_id: str) -> Tuple[str, str, str]:
    """Get presigned URL for S3 upload
    
    Returns:
        Tuple of (presigned_url, object_id, content_type)
    """
    # Ensure allocation uses a concrete storage backend for dynamic get_urls
    storage_id = get_default_storage_id(token)
    # TAMS spec: POST /flows/{flowId}/storage accepts limit and storage_id (no label)
    storage_data = {
        "limit": 1,  # Request only 1 presigned URL
        "storage_id": storage_id
    }
    
    response = requests.post(
        f"{API_BASE_URL}/flows/{flow_id}/storage",
        json=storage_data,
        headers=get_headers(token)
    )
    response.raise_for_status()
    result = response.json()
    
    # Extract presigned URL from response
    # Note: put_url now includes "content-type" per TAMS 8.0 AppNote 0018
    if "media_objects" in result and len(result["media_objects"]) > 0:
        media_obj = result["media_objects"][0]
        object_id = media_obj["object_id"]
        put_url_obj = media_obj["put_url"]
        presigned_url = put_url_obj["url"]
        # Extract content-type from put_url (required for S3 upload header)
        content_type = put_url_obj.get("content-type", "application/octet-stream")
        return presigned_url, object_id, content_type
    else:
        raise ValueError(f"No media_objects in response: {result}")


def upload_to_s3(presigned_url: str, test_data: bytes, content_type: str = "application/octet-stream") -> bool:
    """Upload data to S3 using presigned URL
    
    Args:
        presigned_url: The presigned S3 URL
        test_data: Data to upload
        content_type: Content-Type header value (must match what was used to sign the URL)
    """
    # Set Content-Type header - required when presigned URL includes content-type in signature
    headers = {"Content-Type": content_type}
    response = requests.put(
        presigned_url,
        data=test_data,
        headers=headers
    )
    response.raise_for_status()
    return True


def create_segment(token: str, flow_id: str, object_id: str, 
                  start_seconds: int = 0, duration_seconds: int = 10) -> Dict:
    """Create a segment for the flow"""
    # TAMS timerange format: [start_end) where times are seconds:nanoseconds
    # Format: [start_seconds:nanoseconds_end_seconds:nanoseconds)
    start_time = f"{start_seconds}:0"
    end_time = f"{start_seconds + duration_seconds}:0"
    timerange_str = f"[{start_time}_{end_time})"
    
    segment_data = {
        "object_id": object_id,
        "timerange": {
            "value": timerange_str
        },
        "sample_offset": start_seconds * 25,  # Assuming 25 fps
        "sample_count": duration_seconds * 25,
        "ts_offset": {
            "value": f"{start_seconds}:0"  # Timestamp format: seconds:nanoseconds
        }
    }
    
    response = requests.post(
        f"{API_BASE_URL}/flows/{flow_id}/segments",
        json=segment_data,
        headers=get_headers(token)
    )
    response.raise_for_status()
    result = response.json()
    created_resources["segments"].append((flow_id, object_id))
    return result


def main():
    """Run the complete test data ingestion"""
    print("🧪 Starting Test Data Ingestion\n")
    print("=" * 60)
    
    try:
        # 1. Login
        print("\n1. Logging in...")
        token = login()
        print("✅ Logged in successfully")
        
        # 2. Create 2 sources
        print("\n2. Creating sources...")
        source1 = create_source(token, 1)
        source2 = create_source(token, 2)
        source1_id = source1["id"]
        source2_id = source2["id"]
        
        # 3. Create 4 flows
        print("\n3. Creating flows...")
        # Source 1: 3 flows (2 video, 1 audio)
        flow1 = create_video_flow(token, source1_id, 1, "Primary Video Flow")
        flow2 = create_video_flow(token, source1_id, 2, "Secondary Video Flow")
        flow3 = create_audio_flow(token, source1_id, 1)
        # Source 2: 1 flow
        flow4 = create_video_flow(token, source2_id, 3, "Shared Video Flow")
        
        flow1_id = flow1["id"]
        flow2_id = flow2["id"]  # This flow will share segments with flow4
        flow3_id = flow3["id"]  # Audio flow
        flow4_id = flow4["id"]  # This flow will share segments with flow2
        
        flows = [
            (flow1_id, "Primary Video Flow"),
            (flow2_id, "Secondary Video Flow (shares segments)"),
            (flow3_id, "Audio Flow"),
            (flow4_id, "Shared Video Flow (shares segments)")
        ]
        
        # 4. Create 10 objects via S3 uploads
        print("\n4. Creating objects via S3 uploads...")
        objects_data = []
        
        # Flow 1: 3 objects (segments 0-2)
        for i in range(3):
            presigned_url, object_id, content_type = get_presigned_url(token, flow1_id)
            test_data = f"Test content for object {i} in flow 1".encode()
            upload_to_s3(presigned_url, test_data, content_type)
            objects_data.append((flow1_id, object_id, i))
            created_resources["objects"].append(object_id)
            print(f"✅ Created and uploaded object {i+1}/10: {object_id[:8]}...")
        
        # Flow 2: 3 objects (segments 0-2) - these will be shared with flow4
        shared_objects = []
        for i in range(3):
            presigned_url, object_id, content_type = get_presigned_url(token, flow2_id)
            test_data = f"Test content for shared object {i}".encode()
            upload_to_s3(presigned_url, test_data, content_type)
            objects_data.append((flow2_id, object_id, i))
            shared_objects.append((flow2_id, object_id, i))  # Track for sharing
            created_resources["objects"].append(object_id)
            print(f"✅ Created and uploaded object {i+4}/10: {object_id[:8]}...")
        
        # Flow 3 (Audio): 2 objects (segments 0-1)
        for i in range(2):
            presigned_url, object_id, content_type = get_presigned_url(token, flow3_id)
            test_data = f"Audio test content for object {i}".encode()
            upload_to_s3(presigned_url, test_data, content_type)
            objects_data.append((flow3_id, object_id, i))
            created_resources["objects"].append(object_id)
            print(f"✅ Created and uploaded object {i+7}/10: {object_id[:8]}...")
        
        # Flow 4: 2 new objects (segments 3-4) + will share 3 from flow2
        for i in range(2):
            presigned_url, object_id, content_type = get_presigned_url(token, flow4_id)
            test_data = f"Test content for object {i+3} in flow 4".encode()
            upload_to_s3(presigned_url, test_data, content_type)
            objects_data.append((flow4_id, object_id, i+3))
            created_resources["objects"].append(object_id)
            print(f"✅ Created and uploaded object {i+9}/10: {object_id[:8]}...")
        
        # 5. Create 10 segments
        print("\n5. Creating segments...")
        segments_created = 0
        
        # Flow 1: 3 segments (0-2)
        for flow_id, object_id, segment_idx in objects_data[:3]:
            create_segment(token, flow_id, object_id, start_seconds=segment_idx * 10, duration_seconds=10)
            segments_created += 1
            print(f"✅ Created segment {segments_created}/10: Flow {flow_id[:8]}... Object {object_id[:8]}...")
        
        # Flow 2: 3 segments (0-2) - unique to flow2
        for flow_id, object_id, segment_idx in objects_data[3:6]:
            create_segment(token, flow_id, object_id, start_seconds=segment_idx * 10, duration_seconds=10)
            segments_created += 1
            print(f"✅ Created segment {segments_created}/10: Flow {flow_id[:8]}... Object {object_id[:8]}...")
        
        # Flow 3 (Audio): 2 segments (0-1)
        for flow_id, object_id, segment_idx in objects_data[6:8]:
            create_segment(token, flow_id, object_id, start_seconds=segment_idx * 10, duration_seconds=10)
            segments_created += 1
            print(f"✅ Created segment {segments_created}/10: Flow {flow_id[:8]}... Object {object_id[:8]}...")
        
        # Flow 4: 2 segments (3-4) - unique to flow4
        for flow_id, object_id, segment_idx in objects_data[8:10]:
            create_segment(token, flow_id, object_id, start_seconds=segment_idx * 10, duration_seconds=10)
            segments_created += 1
            print(f"✅ Created segment {segments_created}/10: Flow {flow_id[:8]}... Object {object_id[:8]}...")
        
        # IMPORTANT: Flow 2 and Flow 4 share segments
        # Create the same segments in flow4 that flow2 has (shared segments)
        print("\n6. Creating shared segments (Flow 2 <-> Flow 4)...")
        for flow_id, object_id, segment_idx in shared_objects:
            # Create segment in flow4 with the same object_id (sharing)
            create_segment(token, flow4_id, object_id, start_seconds=segment_idx * 10, duration_seconds=10)
            segments_created += 1
            print(f"✅ Created shared segment {segments_created}/10: Flow {flow4_id[:8]}... (shared Object {object_id[:8]}...)")
        
        print("\n" + "=" * 60)
        print("✅ Test Data Ingestion Completed Successfully!")
        print("=" * 60)
        print("\nSummary:")
        print(f"  📊 Sources: 2")
        print(f"    - Source 1: {source1_id[:8]}... (3 flows)")
        print(f"    - Source 2: {source2_id[:8]}... (1 flow)")
        print(f"  📹 Flows: 4")
        print(f"    - Flow 1 (Video): {flow1_id[:8]}... (3 segments)")
        print(f"    - Flow 2 (Video, shares segments): {flow2_id[:8]}... (3 segments)")
        print(f"    - Flow 3 (Audio): {flow3_id[:8]}... (2 segments)")
        print(f"    - Flow 4 (Video, shares segments): {flow4_id[:8]}... (5 segments: 2 unique + 3 shared)")
        print(f"  📦 Objects: {len(created_resources['objects'])}")
        print(f"  🎬 Segments: {segments_created}")
        print(f"\nNote: Flow 2 and Flow 4 share 3 segments (same object_ids)")
        print(f"\nTo verify, check analytics at: {API_BASE_URL}/analytics/summary")
        
        # Save resource IDs for reference
        with open("test_data_resources.json", "w") as f:
            json.dump({
                "sources": created_resources["sources"],
                "flows": [{"id": flow_id, "label": label} for flow_id, label in flows],
                "objects": created_resources["objects"],
                "segments_count": segments_created
            }, f, indent=2)
        print(f"\n💾 Resource IDs saved to: test_data_resources.json")
        
    except Exception as e:
        print(f"\n❌ Test data ingestion failed: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()

