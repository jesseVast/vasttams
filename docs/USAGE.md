# TAMS API 7.0 - Usage Guide

## Overview
This guide provides comprehensive examples and usage patterns for the TAMS (Time-addressable Media Store) API version 7.0. It covers creating, reading, updating, and deleting sources, flows, and flow-segments with practical examples and expected outputs.

## Base URL
```
http://localhost:8000
```

## API Version
- **Current Version**: 7.0
- **Interactive Documentation**: `/docs` (Swagger UI)
- **ReDoc Documentation**: `/redoc`

---

## 🎬 Sources Management

### Creating Sources

#### Create Single Source
```bash
POST /sources
```

**Request Body:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "format": "urn:x-nmos:format:video",
  "label": "Main Camera 1",
  "description": "Primary studio camera for live broadcasts",
  "created_by": "user@example.com"
}
```

**Expected Response (201 Created):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "format": "urn:x-nmos:format:video",
  "label": "Main Camera 1",
  "description": "Primary studio camera for live broadcasts",
  "created_by": "user@example.com",
  "updated_by": "user@example.com",
  "created": "2024-12-20T10:00:00Z",
  "updated": "2024-12-20T10:00:00Z",
  "tags": {},
  "source_collection": [],
  "collected_by": []
}
```

#### Create Multiple Sources (Batch)
```bash
POST /sources/batch
```

**Request Body:**
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440001",
    "format": "urn:x-nmos:format:video",
    "label": "Camera 2",
    "description": "Secondary camera angle"
  },
  {
    "id": "550e8400-e29b-41d4-a716-446655440002",
    "format": "urn:x-nmos:format:audio",
    "label": "Audio Mix",
    "description": "Mixed audio from all sources"
  }
]
```

**Expected Response (201 Created):**
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440001",
    "format": "urn:x-nmos:format:video",
    "label": "Camera 2",
    "description": "Secondary camera angle",
    "created": "2024-12-20T10:00:00Z",
    "updated": "2024-12-20T10:00:00Z"
  },
  {
    "id": "550e8400-e29b-41d4-a716-446655440002",
    "format": "urn:x-nmos:format:audio",
    "label": "Audio Mix",
    "description": "Mixed audio from all sources",
    "created": "2024-12-20T10:00:00Z",
    "updated": "2024-12-20T10:00:00Z"
  }
]
```

### Reading Sources

#### List All Sources
```bash
GET /sources
```

**Expected Response (200 OK):**
```json
{
  "data": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "format": "urn:x-nmos:format:video",
      "label": "Main Camera 1",
      "description": "Primary studio camera for live broadcasts"
    },
    {
      "id": "550e8400-e29b-41d4-a716-446655440001",
      "format": "urn:x-nmos:format:video",
      "label": "Camera 2",
      "description": "Secondary camera angle"
    }
  ],
  "paging": {
    "next": null,
    "limit": 100
  }
}
```

#### Get Source by ID
```bash
GET /sources/{source_id}
```

**Expected Response (200 OK):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "format": "urn:x-nmos:format:video",
  "label": "Main Camera 1",
  "description": "Primary studio camera for live broadcasts",
  "created_by": "user@example.com",
  "updated_by": "user@example.com",
  "created": "2024-12-20T10:00:00Z",
  "updated": "2024-12-20T10:00:00Z",
  "tags": {},
  "source_collection": [],
  "collected_by": []
}
```

#### Filter Sources
```bash
GET /sources?format=urn:x-nmos:format:video&label=Main Camera
```

**Expected Response (200 OK):**
```json
{
  "data": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "format": "urn:x-nmos:format:video",
      "label": "Main Camera 1",
      "description": "Primary studio camera for live broadcasts"
    }
  ],
  "paging": {
    "next": null,
    "limit": 100
  }
}
```

### Updating Sources

#### Update Source Description
```bash
PUT /sources/{source_id}/description
```

**Request Body:**
```json
"Updated description for the main camera"
```

**Expected Response (200 OK):**
```json
"Updated description for the main camera"
```

#### Update Source Label
```bash
PUT /sources/{source_id}/label
```

**Request Body:**
```json
"Main Camera 1 - Updated"
```

**Expected Response (200 OK):**
```json
"Main Camera 1 - Updated"
```

#### Update Source Tags
```bash
PUT /sources/{source_id}/tags
```

**Request Body:**
```json
{
  "location": "Studio A",
  "priority": "high",
  "equipment": "Sony FX9"
}
```

**Expected Response (200 OK):**
```json
{
  "location": "Studio A",
  "priority": "high",
  "equipment": "Sony FX9"
}
```

### Deleting Sources

#### Delete Source
```bash
DELETE /sources/{source_id}
```

**Expected Response (204 No Content)**

**Note:** This performs a soft delete by default. The source is marked as deleted but remains in the database.

---

## 🌊 Flows Management

### Creating Flows

#### Create Single Flow
```bash
POST /flows
```

**Request Body (Video Flow):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440010",
  "source_id": "550e8400-e29b-41d4-a716-446655440000",
  "format": "urn:x-nmos:format:video",
  "codec": "video/H.264",
  "label": "Main Video Stream",
  "description": "Primary video stream from main camera",
  "frame_width": 1920,
  "frame_height": 1080,
  "frame_rate": "25/1",
  "container": "video/MP4",
  "created_by": "user@example.com"
}
```

**Expected Response (201 Created):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440010",
  "source_id": "550e8400-e29b-41d4-a716-446655440000",
  "format": "urn:x-nmos:format:video",
  "codec": "video/H.264",
  "label": "Main Video Stream",
  "description": "Primary video stream from main camera",
  "frame_width": 1920,
  "frame_height": 1080,
  "frame_rate": "25/1",
  "container": "video/MP4",
  "created_by": "user@example.com",
  "updated_by": "user@example.com",
  "created": "2024-12-20T10:00:00Z",
  "updated": "2024-12-20T10:00:00Z",
  "tags": {},
  "read_only": false,
  "max_bit_rate": null,
  "avg_bit_rate": null
}
```

#### Create Multiple Flows (Batch)
```bash
POST /flows/batch
```

**Request Body:**
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440011",
    "source_id": "550e8400-e29b-41d4-a716-446655440001",
    "format": "urn:x-nmos:format:video",
    "codec": "video/H.264",
    "label": "Camera 2 Stream",
    "frame_width": 1920,
    "frame_height": 1080,
    "frame_rate": "25/1"
  },
  {
    "id": "550e8400-e29b-41d4-a716-446655440012",
    "source_id": "550e8400-e29b-41d4-a716-446655440002",
    "format": "urn:x-nmos:format:audio",
    "codec": "audio/AAC",
    "label": "Audio Stream",
    "sample_rate": 48000,
    "bits_per_sample": 24,
    "channels": 2
  }
]
```

**Expected Response (201 Created):**
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440011",
    "source_id": "550e8400-e29b-41d4-a716-446655440001",
    "format": "urn:x-nmos:format:video",
    "codec": "video/H.264",
    "label": "Camera 2 Stream",
    "frame_width": 1920,
    "frame_height": 1080,
    "frame_rate": "25/1"
  },
  {
    "id": "550e8400-e29b-41d4-a716-446655440012",
    "source_id": "550e8400-e29b-41d4-a716-446655440002",
    "format": "urn:x-nmos:format:audio",
    "codec": "audio/AAC",
    "label": "Audio Stream",
    "sample_rate": 48000,
    "bits_per_sample": 24,
    "channels": 2
  }
]
```

### Reading Flows

#### List All Flows
```bash
GET /flows
```

**Expected Response (200 OK):**
```json
{
  "data": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440010",
      "source_id": "550e8400-e29b-41d4-a716-446655440000",
      "format": "urn:x-nmos:format:video",
      "codec": "video/H.264",
      "label": "Main Video Stream"
    },
    {
      "id": "550e8400-e29b-41d4-a716-446655440011",
      "source_id": "550e8400-e29b-41d4-a716-446655440001",
      "format": "urn:x-nmos:format:video",
      "codec": "video/H.264",
      "label": "Camera 2 Stream"
    }
  ],
  "paging": {
    "next": null,
    "limit": 100
  }
}
```

#### Get Flow by ID
```bash
GET /flows/{flow_id}
```

**Expected Response (200 OK):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440010",
  "source_id": "550e8400-e29b-41d4-a716-446655440000",
  "format": "urn:x-nmos:format:video",
  "codec": "video/H.264",
  "label": "Main Video Stream",
  "description": "Primary video stream from main camera",
  "frame_width": 1920,
  "frame_height": 1080,
  "frame_rate": "25/1",
  "container": "video/MP4",
  "created_by": "user@example.com",
  "updated_by": "user@example.com",
  "created": "2024-12-20T10:00:00Z",
  "updated": "2024-12-20T10:00:00Z",
  "tags": {},
  "read_only": false,
  "max_bit_rate": null,
  "avg_bit_rate": null
}
```

#### Filter Flows
```bash
GET /flows?source_id=550e8400-e29b-41d4-a716-446655440000&format=urn:x-nmos:format:video
```

**Expected Response (200 OK):**
```json
{
  "data": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440010",
      "source_id": "550e8400-e29b-41d4-a716-446655440000",
      "format": "urn:x-nmos:format:video",
      "codec": "video/H.264",
      "label": "Main Video Stream"
    }
  ],
  "paging": {
    "next": null,
    "limit": 100
  }
}
```

### Updating Flows

#### Update Flow
```bash
PUT /flows/{flow_id}
```

**Request Body:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440010",
  "source_id": "550e8400-e29b-41d4-a716-446655440000",
  "format": "urn:x-nmos:format:video",
  "codec": "video/H.264",
  "label": "Main Video Stream - Updated",
  "description": "Updated description for main video stream",
  "frame_width": 1920,
  "frame_height": 1080,
  "frame_rate": "25/1",
  "container": "video/MP4"
}
```

**Expected Response (200 OK):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440010",
  "source_id": "550e8400-e29b-41d4-a716-446655440000",
  "format": "urn:x-nmos:format:video",
  "codec": "video/H.264",
  "label": "Main Video Stream - Updated",
  "description": "Updated description for main video stream",
  "frame_width": 1920,
  "frame_height": 1080,
  "frame_rate": "25/1",
  "container": "video/MP4",
  "updated": "2024-12-20T11:00:00Z"
}
```

#### Update Flow Properties
```bash
PUT /flows/{flow_id}/max_bit_rate
```

**Request Body:**
```json
5000000
```

**Expected Response (200 OK):**
```json
5000000
```

#### Update Flow Tags
```bash
PUT /flows/{flow_id}/tags
```

**Request Body:**
```json
{
  "quality": "high",
  "stream_type": "live",
  "priority": "primary"
}
```

**Expected Response (200 OK):**
```json
{
  "quality": "high",
  "stream_type": "live",
  "priority": "primary"
}
```

### Deleting Flows

#### Delete Flow
```bash
DELETE /flows/{flow_id}
```

**Expected Response (204 No Content)**

**Note:** This performs a soft delete by default. The flow is marked as deleted but remains in the database.

---

## 🎯 Flow Segments Management

### Creating Flow Segments

#### Create Flow Segment
```bash
POST /flows/{flow_id}/segments
```

**Request Body:**
```json
{
  "object_id": "550e8400-e29b-41d4-a716-446655440020",
  "timerange": "[2024-12-20T10:00:00Z:2024-12-20T10:00:10Z)",
  "sample_offset": 0,
  "sample_count": 250,
  "storage_path": "flows/550e8400-e29b-41d4-a716-446655440010/2024/12/20/550e8400-e29b-41d4-a716-446655440020",
  "key_frame_count": 1
}
```

**Expected Response (201 Created):**
```json
{
  "object_id": "550e8400-e29b-41d4-a716-446655440020",
  "timerange": "[2024-12-20T10:00:00Z:2024-12-20T10:00:10Z)",
  "sample_offset": 0,
  "sample_count": 250,
  "storage_path": "flows/550e8400-e29b-41d4-a716-446655440010/2024/12/20/550e8400-e29b-41d4-a716-446655440020",
  "key_frame_count": 1,
  "ts_offset": null,
  "last_duration": null,
  "get_urls": [
    {
      "storage_id": "550e8400-e29b-41d4-a716-446655440030",
      "url": "http://localhost:8000/objects/550e8400-e29b-41d4-a716-446655440020/download",
      "presigned": false,
      "label": "default",
      "controlled": true
    }
  ]
}
```

### Reading Flow Segments

#### List Flow Segments
```bash
GET /flows/{flow_id}/segments
```

**Expected Response (200 OK):**
```json
[
  {
    "object_id": "550e8400-e29b-41d4-a716-446655440020",
    "timerange": "[2024-12-20T10:00:00Z:2024-12-20T10:00:10Z)",
    "sample_offset": 0,
    "sample_count": 250,
    "storage_path": "flows/550e8400-e29b-41d4-a716-446655440010/2024/12/20/550e8400-e29b-41d4-a716-446655440020",
    "key_frame_count": 1
  },
  {
    "object_id": "550e8400-e29b-41d4-a716-446655440021",
    "timerange": "[2024-12-20T10:00:10Z:2024-12-20T10:00:20Z)",
    "sample_offset": 250,
    "sample_count": 250,
    "storage_path": "flows/550e8400-e29b-41d4-a716-446655440010/2024/12/20/550e8400-e29b-41d4-a716-446655440021",
    "key_frame_count": 1
  }
]
```

#### Filter Segments by Timerange
```bash
GET /flows/{flow_id}/segments?timerange=[2024-12-20T10:00:00Z:2024-12-20T10:00:15Z)
```

**Expected Response (200 OK):**
```json
[
  {
    "object_id": "550e8400-e29b-41d4-a716-446655440020",
    "timerange": "[2024-12-20T10:00:00Z:2024-12-20T10:00:10Z)",
    "sample_offset": 0,
    "sample_count": 250,
    "storage_path": "flows/550e8400-e29b-41d4-a716-446655440010/2024/12/20/550e8400-e29b-41d4-a716-446655440020",
    "key_frame_count": 1
  }
]
```

### Deleting Flow Segments

#### Delete Flow Segments
```bash
DELETE /flows/{flow_id}/segments
```

**Query Parameters:**
- `timerange` (optional): Delete segments within specific time range
- `soft_delete` (optional): Default true, set to false for hard delete
- `deleted_by` (optional): User/system performing deletion

**Expected Response (204 No Content)**

**Note:** This performs a soft delete by default. Segments are marked as deleted but remain in the database.

---

## 💾 Storage Allocation and Management

### Overview
Storage allocation in TAMS involves allocating storage locations for writing media objects. The system provides PUT URLs for uploading media objects and may include actions for creating buckets and setting CORS properties.

### Storage Allocation Process

#### Step 1: Allocate Storage Space
```bash
POST /flows/{flow_id}/storage
```

**Request Body:**
```json
{
  "object_ids": ["550e8400-e29b-41d4-a716-446655440020"],
  "storage_id": "optional-storage-backend-uuid",
  "limit": 100
}
```

**Expected Response (201 Created):**
```json
{
  "pre": [
    {
      "action": "create_bucket",
      "bucket_id": "bucket-name",
      "put_url": {
        "method": "PUT",
        "url": "https://storage.example.com/bucket-name",
        "headers": {}
      },
      "put_cors_url": {
        "method": "PUT",
        "url": "https://storage.example.com/bucket-name?cors",
        "headers": {}
      }
    }
  ],
  "media_objects": [
    {
      "object_id": "550e8400-e29b-41d4-a716-446655440020",
      "put_url": {
        "method": "PUT",
        "url": "https://storage.example.com/bucket-name/550e8400-e29b-41d4-a716-446655440020",
        "headers": {}
      },
      "put_cors_url": {
        "method": "PUT",
        "url": "https://storage.example.com/bucket-name/550e8400-e29b-41d4-a716-446655440020?cors",
        "headers": {}
      }
    }
  ]
}
```

#### Step 2: Upload Content Using PUT URL
```bash
# Upload content directly to the storage backend using the PUT URL
curl -X PUT "https://storage.example.com/bucket-name/550e8400-e29b-41d4-a716-446655440020" \
  -H "Content-Type: video/mp4" \
  -T "video_segment.mp4"
```

#### Step 3: Register Flow Segment
```bash
POST /flows/{flow_id}/segments
```

**Request Body:**
```json
{
  "object_id": "550e8400-e29b-41d4-a716-446655440020",
  "timerange": "[2024-12-20T10:00:00Z:2024-12-20T10:15:00Z)",
  "sample_offset": 0,
  "sample_count": 250,
  "key_frame_count": 1
}
```

**Note:** The flow segment registration confirms that the upload is complete and makes the media object available for retrieval.

### Batch Storage Allocation

#### Allocate Multiple Objects
```bash
POST /flows/{flow_id}/storage/batch
```

**Request Body:**
```json
[
  {
    "flow_id": "550e8400-e29b-41d4-a716-446655440010",
    "size_bytes": 536870912,
    "content_type": "video/mp4",
    "timerange": "[2024-12-20T10:00:00Z:2024-12-20T10:07:30Z)"
  },
  {
    "flow_id": "550e8400-e29b-41d4-a716-446655440010",
    "size_bytes": 536870912,
    "content_type": "video/mp4",
    "timerange": "[2024-12-20T10:07:30Z:2024-12-20T10:15:00Z)"
  }
]
```

**Expected Response (201 Created):**
```json
[
  {
    "allocation_id": "alloc-550e8400-e29b-41d4-a716-446655440031",
    "object_id": "550e8400-e29b-41d4-a716-446655440021",
    "storage_path": "550e8400-e29b-41d4-a716-446655440010/2024/12/20/550e8400-e29b-41d4-a716-446655440021",
    "presigned_upload_url": "https://s3.example.com/upload?presigned=...",
    "expires_at": "2024-12-20T11:00:00Z",
    "status": "allocated"
  },
  {
    "allocation_id": "alloc-550e8400-e29b-41d4-a716-446655440032",
    "object_id": "550e8400-e29b-41d4-a716-446655440022",
    "storage_path": "550e8400-e29b-41d4-a716-446655440010/2024/12/20/550e8400-e29b-41d4-a716-446655440022",
    "presigned_upload_url": "https://s3.example.com/upload?presigned=...",
    "expires_at": "2024-12-20T11:00:00Z",
    "status": "allocated"
  }
]
```

### Storage Path Structure

#### Automatic Path Generation
TAMS automatically generates hierarchical storage paths based on:
- **Flow ID**: Unique identifier for the flow
- **Date**: Year/month/day from the timerange
- **Object ID**: Unique identifier for the object

**Path Format**: `{flow_id}/{year:04d}/{month:02d}/{day:02d}/{object_id}`

**Example Paths**:
```
550e8400-e29b-41d4-a716-446655440010/2024/12/20/550e8400-e29b-41d4-a716-446655440020
550e8400-e29b-41d4-a716-446655440010/2024/12/20/550e8400-e29b-41d4-a716-446655440021
550e8400-e29b-41d4-a716-446655440010/2024/12/20/550e8400-e29b-41d4-a716-446655440022
```

#### Custom Storage Paths
You can specify custom storage paths during allocation:

**Request Body with Custom Path:**
```json
{
  "flow_id": "550e8400-e29b-41d4-a716-446655440010",
  "size_bytes": 1073741824,
  "storage_path": "custom/path/video_segment_001",
  "content_type": "video/mp4"
}
```

### Storage Backend Information

#### Check Available Storage Backends
```bash
GET /service/storage-backends
```

**Expected Response (200 OK):**
```json
{
  "storage_backends": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440030",
      "name": "default-storage",
      "type": "http_object_store",
      "default": true
    }
  ]
}
```

### Object Information

#### Get Object Information
```bash
GET /objects/{object_id}
```

**Expected Response (200 OK):**
```json
{
  "flow_references": [
    {
      "flow_id": "550e8400-e29b-41d4-a716-446655440010",
      "timerange": "[2024-12-20T10:00:00Z:2024-12-20T10:15:00Z)"
    }
  ]
}
```

**Note:** This endpoint returns information about which flows reference a specific media object, including the timerange for each reference.

### Error Handling for Storage Operations

#### Common Storage Errors

**Invalid Flow Storage Request (400 Bad Request):**
```json
{
  "detail": "Bad request. Invalid flow storage request JSON or the flow 'container' is not set."
}
```

**Object ID Already Exists (400 Bad Request):**
```json
{
  "detail": "If object_ids supplied, some or all already exist."
}
```

**Flow Not Found (404 Not Found):**
```json
{
  "detail": "The requested flow does not exist."
}
```

**Flow Read-Only (403 Forbidden):**
```json
{
  "detail": "Forbidden. You do not have permission to modify this flow. It may be marked read-only."
}
```

### Best Practices for Storage Allocation

#### 1. **Plan Object IDs**
- Generate unique object IDs before allocation
- Ensure object IDs are not already in use
- Consider using UUIDs for uniqueness

#### 2. **Handle Pre-Actions**
- Check for bucket creation requirements
- Set CORS properties if needed
- Complete pre-actions before uploading

#### 3. **Use PUT URLs Correctly**
- Upload directly to the provided PUT URL
- Include appropriate Content-Type headers
- Handle upload failures gracefully

#### 4. **Register Flow Segments Promptly**
- Register segments after successful upload
- Include accurate timerange information
- Handle registration failures appropriately

#### 5. **Monitor Storage Backends**
- Check available storage backends
- Use appropriate storage_id for specific needs
- Handle storage backend failures



### Python Client Example

```python
import requests
import time
from typing import List, Dict

class TAMSStorageClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {api_key}"}
    
    def allocate_storage(self, flow_id: str, object_ids: List[str], 
                        storage_id: str = None) -> Dict:
        """Allocate storage for objects in a flow"""
        payload = {
            "object_ids": object_ids
        }
        if storage_id:
            payload["storage_id"] = storage_id
        
        response = requests.post(
            f"{self.base_url}/flows/{flow_id}/storage",
            json=payload,
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()
    
    def upload_content(self, put_url: str, file_path: str, content_type: str = "application/octet-stream") -> bool:
        """Upload content using PUT URL"""
        try:
            with open(file_path, 'rb') as f:
                headers = {"Content-Type": content_type}
                response = requests.put(put_url, data=f, headers=headers)
                response.raise_for_status()
                return True
        except Exception as e:
            print(f"Upload failed: {e}")
            return False
    
    def create_flow_segment(self, flow_id: str, object_id: str, 
                           timerange: str, sample_offset: int = 0, 
                           sample_count: int = 0, key_frame_count: int = 0) -> Dict:
        """Create flow segment after successful upload"""
        payload = {
            "object_id": object_id,
            "timerange": timerange,
            "sample_offset": sample_offset,
            "sample_count": sample_count,
            "key_frame_count": key_frame_count
        }
        
        response = requests.post(
            f"{self.base_url}/flows/{flow_id}/segments",
            json=payload,
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()

# Usage example
client = TAMSStorageClient("http://localhost:8000", "your-api-key")

# Allocate storage
allocation = client.allocate_storage(
    flow_id="550e8400-e29b-41d4-a716-446655440010",
    object_ids=["550e8400-e29b-41d4-a716-446655440020"]
)

# Check if bucket creation is needed
if allocation.get("pre"):
    for action in allocation["pre"]:
        if action["action"] == "create_bucket":
            print(f"Bucket {action['bucket_id']} needs to be created")

# Upload content using the first media object's PUT URL
if allocation.get("media_objects"):
    media_object = allocation["media_objects"][0]
    put_url = media_object["put_url"]["url"]
    
    success = client.upload_content(
        put_url,
        "video_segment.mp4",
        "video/mp4"
    )
    
    if success:
        # Create flow segment after successful upload
        segment = client.create_flow_segment(
            flow_id="550e8400-e29b-41d4-a716-446655440010",
            object_id=media_object["object_id"],
            timerange="[2024-12-20T10:00:00Z:2024-12-20T10:15:00Z)",
            sample_offset=0,
            sample_count=250,
            key_frame_count=1
        )
        print(f"Flow segment created: {segment}")
```

### cURL Examples

#### Allocate Storage
```bash
curl -X POST "http://localhost:8000/flows/550e8400-e29b-41d4-a716-446655440010/storage" \
  -H "Authorization: Bearer your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "object_ids": ["550e8400-e29b-41d4-a716-446655440020"]
  }'
```

#### Check Storage Backends
```bash
curl -X GET "http://localhost:8000/service/storage-backends" \
  -H "Authorization: Bearer your-api-key"
```

#### Get Object Information
```bash
curl -X GET "http://localhost:8000/objects/550e8400-e29b-41d4-a716-446655440020" \
  -H "Authorization: Bearer your-api-key"
```

---

## 🔄 Building Flows with Existing Segments

### Overview
This section explains how to build new flows by reusing existing flow-segments or objects. In the TAMS architecture, you work with **flow-segments** that reference existing objects, not directly with objects.

### Architecture Relationship
```
Source → Flow → Flow Segments → Objects
```

- **Objects**: Raw media files stored in S3
- **Flow Segments**: Metadata that links objects to flows  
- **Flows**: Collections of segments representing a media stream

### Step-by-Step Process

#### Step 1: Create the New Flow
```bash
POST /flows
```

**Request Body:**
```json
{
  "id": "new-flow-uuid",
  "source_id": "existing-source-uuid",
  "format": "urn:x-nmos:format:video",
  "codec": "video/H.264",
  "label": "New Flow from Existing Segments",
  "description": "Flow created from existing segments",
  "frame_width": 1920,
  "frame_height": 1080,
  "frame_rate": "25/1"
}
```

**Response:** 201 Created with the new flow details

#### Step 2: Create Flow Segments (Pointing to Existing Objects)
```bash
POST /flows/{flow_id}/segments
```

**Request Body:**
```json
{
  "object_id": "existing-object-uuid",
  "timerange": "[2024-01-01T10:00:00Z:2024-01-01T10:00:10Z)",
  "sample_offset": 0,
  "sample_count": 300,
  "storage_path": "existing-s3-path"
}
```

**Important Fields:**
- `object_id`: Must reference an existing object
- `storage_path`: Must match where the object actually exists in S3
- `timerange`: Should align with the object's content

### Complete Example Workflow

#### Python Example
```python
import uuid
import requests

# Base URL
base_url = "http://localhost:8000"

# 1. Create new flow
new_flow = {
    "id": str(uuid.uuid4()),
    "source_id": "existing-source-id",
    "format": "urn:x-nmos:format:video",
    "codec": "video/H.264",
    "label": "New Flow from Existing Content",
    "frame_width": 1920,
    "frame_height": 1080,
    "frame_rate": "25/1"
}

# Create the flow
flow_response = requests.post(f"{base_url}/flows", json=new_flow)
flow_id = flow_response.json()["id"]

# 2. Create segments pointing to existing objects
existing_segments = [
    {
        "object_id": "existing-object-1",
        "timerange": "[2024-01-01T10:00:00Z:2024-01-01T10:00:10Z)",
        "storage_path": "existing-s3-path-1",
        "sample_offset": 0,
        "sample_count": 250
    },
    {
        "object_id": "existing-object-2",
        "timerange": "[2024-01-01T10:00:10Z:2024-01-01T10:00:20Z)",
        "storage_path": "existing-s3-path-2",
        "sample_offset": 0,
        "sample_count": 250
    }
]

# Create flow segments for each existing object
for segment_data in existing_segments:
    response = requests.post(
        f"{base_url}/flows/{flow_id}/segments",
        json=segment_data
    )
    print(f"Created segment: {response.status_code}")
```

#### cURL Example
```bash
# 1. Create new flow
curl -X POST "http://localhost:8000/flows" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "source_id": "existing-source-uuid",
    "format": "urn:x-nmos:format:video",
    "codec": "video/H.264",
    "label": "New Flow",
    "frame_width": 1920,
    "frame_height": 1080,
    "frame_rate": "25/1"
  }'

# 2. Create segment pointing to existing object
curl -X POST "http://localhost:8000/flows/550e8400-e29b-41d4-a716-446655440000/segments" \
  -H "Content-Type: application/json" \
  -d '{
    "object_id": "existing-object-uuid",
    "timerange": "[2024-01-01T10:00:00Z:2024-01-01T10:00:10Z)",
    "storage_path": "existing-s3-path",
    "sample_offset": 0,
    "sample_count": 250
  }'
```

### Key Benefits

1. **Reusability**: Multiple flows can reference the same media objects
2. **Efficiency**: No need to duplicate media files or storage
3. **Flexibility**: Create different flow arrangements from existing content
4. **Data Integrity**: Objects remain unchanged, only metadata relationships change

### Important Considerations

#### Storage Path Consistency
- **Critical**: The `storage_path` must match where objects actually exist in S3
- **Verification**: Use the object's actual S3 key, not a generated path
- **Consistency**: Ensure storage and retrieval use the same paths

#### Object Validation
- **Existence Check**: Verify referenced objects exist before creating segments
- **Access Rights**: Ensure you have permission to reference the objects
- **Metadata Alignment**: Confirm object metadata matches segment requirements

#### Timerange Coordination
- **Content Alignment**: Segment timeranges should align with object content
- **Continuity**: Ensure segments form a continuous timeline if needed
- **Overlap Handling**: Handle any timerange overlaps appropriately

### Common Use Cases

1. **Content Repurposing**: Create new flows from existing media content
2. **Playlist Creation**: Build flows representing different content sequences
3. **Archive Management**: Organize existing content into logical flows
4. **Content Versioning**: Create alternative flow arrangements

### Error Handling

#### Common Issues
- **404 Object Not Found**: Referenced object doesn't exist
- **400 Invalid Storage Path**: Storage path doesn't match object location
- **403 Permission Denied**: No access to referenced object
- **409 Conflict**: Object already referenced by another flow

#### Best Practices
- **Validate First**: Check object existence before creating segments
- **Test Paths**: Verify storage paths resolve correctly
- **Handle Errors**: Implement proper error handling for failed operations
- **Rollback Strategy**: Plan for segment creation failures

---

## 📊 Analytics Examples

### Flow Usage Analytics
```bash
GET /flow-usage
```

**Expected Response (200 OK):**
```json
{
  "total_flows": 150,
  "active_flows": 142,
  "deleted_flows": 8,
  "flows_by_format": {
    "urn:x-nmos:format:video": 120,
    "urn:x-nmos:format:audio": 25,
    "urn:x-tam:format:image": 5
  },
  "flows_by_source": {
    "550e8400-e29b-41d4-a716-446655440000": 45,
    "550e8400-e29b-41d4-a716-446655440001": 38,
    "550e8400-e29b-41d4-a716-446655440002": 67
  }
}
```

### Storage Usage Analytics
```bash
GET /storage-usage
```

**Expected Response (200 OK):**
```json
{
  "total_objects": 1250,
  "total_size_bytes": 1073741824000,
  "objects_by_flow": {
    "550e8400-e29b-41d4-a716-446655440010": 45,
    "550e8400-e29b-41d4-a716-446655440011": 38,
    "550e8400-e29b-41d4-a716-446655440012": 67
  },
  "storage_by_month": {
    "2024-12": 1073741824000,
    "2024-11": 858993459200,
    "2024-10": 644245094400
  }
}
```

### Time Range Analysis
```bash
GET /time-range-analysis?flow_id=550e8400-e29b-41d4-a716-446655440010
```

**Expected Response (200 OK):**
```json
{
  "flow_id": "550e8400-e29b-41d4-a716-446655440010",
  "total_segments": 45,
  "total_duration_seconds": 450,
  "coverage_percentage": 95.2,
  "gaps": [
    {
      "start": "2024-12-20T10:15:30Z",
      "end": "2024-12-20T10:15:45Z",
      "duration_seconds": 15
    }
  ],
  "overlaps": [],
  "time_distribution": {
    "hourly": {
      "10": 180,
      "11": 270
    }
  }
}
```

---

## 🔧 Error Handling

### Common HTTP Status Codes

- **200 OK**: Request successful
- **201 Created**: Resource created successfully
- **204 No Content**: Request successful, no response body
- **400 Bad Request**: Invalid request data
- **401 Unauthorized**: Authentication required
- **403 Forbidden**: Access denied
- **404 Not Found**: Resource not found
- **409 Conflict**: Resource conflict
- **500 Internal Server Error**: Server error

### Error Response Format
```json
{
  "detail": "Error message describing the issue",
  "error_code": "ERROR_CODE",
  "timestamp": "2024-12-20T10:00:00Z"
}
```

### Validation Errors
```json
{
  "detail": [
    {
      "loc": ["body", "frame_width"],
      "msg": "field required",
      "type": "value_error.missing"
    },
    {
      "loc": ["body", "frame_height"],
      "msg": "ensure this value is greater than 0",
      "type": "value_error.number.not_gt",
      "ctx": {"limit_value": 0}
    }
  ]
}
```

---

## 📚 Best Practices

### General Guidelines

1. **Use UUIDs**: Always use proper UUIDs for IDs
2. **Validate Input**: Validate all input data before sending
3. **Handle Errors**: Implement proper error handling for all API calls
4. **Use Batch Operations**: Use batch endpoints for multiple resources
5. **Monitor Responses**: Check response status codes and handle accordingly

### Performance Tips

1. **Pagination**: Use pagination for large result sets
2. **Filtering**: Use query parameters to filter results
3. **Batch Operations**: Use batch endpoints for bulk operations
4. **Connection Reuse**: Reuse HTTP connections when possible

### Security Considerations

1. **Authentication**: Always include proper authentication headers
2. **Input Validation**: Validate all input data on the client side
3. **Error Handling**: Don't expose sensitive information in error messages
4. **Rate Limiting**: Respect rate limits and implement backoff strategies

---

*Last Updated: December 2024*  
*TAMS API Version: 7.0*  
*Status: Production Ready*
