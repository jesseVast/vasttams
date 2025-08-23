# TAMS Sample Workflow Documentation

This document provides a complete sample workflow demonstrating the TAMS API integration, including detailed API calls, requests, and responses for creating sources, flows, segments, and uploading files.

## Overview

The sample workflow demonstrates the **complete TAMS lifecycle** including:
1. **Source Creation** - Creating a media source
2. **Flow Creation** - Creating video flows linked to the source
3. **Segment Creation** - Adding flow segments with metadata
4. **File Upload** - Uploading media files via multipart form data
5. **Dependency Validation** - Testing foreign key constraints and relationships
6. **Flow Management** - Creating additional flows using existing segments
7. **Data Retrieval** - Testing if flows can access their associated data
8. **Deletion Workflow** - Testing proper cleanup order and dependency enforcement
9. **Final State Verification** - Ensuring proper cleanup and data integrity

## Test Environment

- **Base URL**: `http://localhost:8000`
- **VAST Database**: `http://172.200.204.90`
- **S3 Storage**: `http://172.200.204.91`
- **Test File**: 3KB MP4 video segment

## Complete Workflow Example

The complete TAMS workflow consists of **10 main steps** that test the entire lifecycle from creation through deletion. This includes dependency validation, proper cleanup order, and data integrity verification.

### **Phase 1: Creation and Setup**

#### Step 1: Creating Source via HTTP API

**Request:**
```http
POST http://localhost:8000/sources
Content-Type: application/json

{
  "id": "32cffed8-2015-4e89-a2d7-4395b1b1c1f5",
  "format": "urn:x-nmos:format:video",
  "label": "HTTP API Test Source",
  "description": "Source for testing HTTP API workflow"
}
```

**Response:**
```json
{
  "id": "32cffed8-2015-4e89-a2d7-4395b1b1c1f5",
  "format": "urn:x-nmos:format:video",
  "label": "HTTP API Test Source",
  "description": "Source for testing HTTP API workflow",
  "created": "2025-08-17T02:58:16.738844+00:00",
  "updated": "2025-08-17T02:58:16.738844+00:00",
  "tags": {},
  "source_collection": [],
  "collected_by": []
}
```

**Status**: `201 Created`

---

### Step 2: Creating Flow via HTTP API

**Request:**
```http
POST http://localhost:8000/flows
Content-Type: application/json

{
  "id": "0e9c9b8f-488f-4428-8867-2bc2550612c7",
  "source_id": "32cffed8-2015-4e89-a2d7-4395b1b1c1f5",
  "format": "urn:x-nmos:format:video",
  "codec": "video/mp4",
  "frame_width": 1920,
  "frame_height": 1080,
  "frame_rate": "25/1",
  "label": "HTTP API Test Flow",
  "description": "Flow for testing HTTP API workflow"
}
```

**Response:**
```json
{
  "id": "0e9c9b8f-488f-4428-8867-2bc2550612c7",
  "source_id": "32cffed8-2015-4e89-a2d7-4395b1b1c1f5",
  "format": "urn:x-nmos:format:video",
  "codec": "video/mp4",
  "label": "HTTP API Test Flow",
  "description": "Flow for testing HTTP API workflow",
  "frame_width": 1920,
  "frame_height": 1080,
  "frame_rate": "25/1",
  "read_only": false,
  "created": "2025-08-17T02:58:17.242588+00:00",
  "updated": "2025-08-17T02:58:17.242588+00:00",
  "tags": {},
  "flow_collection": null
}
```

**Status**: `201 Created`

---

### Step 3: Creating Test File

**File Details:**
- **Path**: `/var/folders/c4/jr_mt6r16vz32g9wtld4ldxm0000gn/T/tmpine97fh4.mp4`
- **Size**: 3072 bytes (3KB)
- **Content**: Test video segment data

---

### Step 4: Creating Segment via HTTP API (Multipart Form Data)

**Request:**
```http
POST http://localhost:8000/flows/0e9c9b8f-488f-4428-8867-2bc2550612c7/segments
Content-Type: multipart/form-data

--boundary
Content-Disposition: form-data; name="segment"
Content-Type: application/json

{
  "object_id": "9e57802a-3e84-4f5c-943c-0a74fa1f1909",
  "timerange": "[0:0_10:0)",
  "sample_offset": 0,
  "sample_count": 250
}

--boundary
Content-Disposition: form-data; name="file"; filename="test_segment.mp4"
Content-Type: video/mp4

[Binary file content]
--boundary--
```

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440002",
  "flow_id": "0e9c9b8f-488f-4428-8867-2bc2550612c7",
  "object_id": "9e57802a-3e84-4f5c-943c-0a74fa1f1909",
  "timerange": "[0:0_10:0)",
  "sample_offset": 0,
  "sample_count": 250,
  "storage_path": "tams/2025/08/17/0e9c9b8f-488f-4428-8867-2bc2550612c7/9e57802a-3e84-4f5c-943c-0a74fa1f1909.mp4",
  "file_size": 3072,
  "content_type": "video/mp4",
  "created": "2025-08-17T02:58:18.123456+00:00",
  "updated": "2025-08-17T02:58:18.123456+00:00"
}
```

**Status**: `201 Created`

**Key Information:**
- **Segment ID**: Automatically generated
- **Storage Path**: Automatically organized by date and flow
- **File Size**: 3072 bytes (3KB)
- **Content Type**: video/mp4

---

### Step 5: Verifying Segment Creation

**Request:**
```http
GET http://localhost:8000/flows/0e9c9b8f-488f-4428-8867-2bc2550612c7/segments
```

**Response:**
```json
{
  "data": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440002",
      "flow_id": "0e9c9b8f-488f-4428-8867-2bc2550612c7",
      "object_id": "9e57802a-3e84-4f5c-943c-0a74fa1f1909",
      "timerange": "[0:0_10:0)",
      "sample_offset": 0,
      "sample_count": 250,
      "storage_path": "tams/2025/08/17/0e9c9b8f-488f-4428-8867-2bc2550612c7/9e57802a-3e84-4f5c-943c-0a74fa1f1909.mp4",
      "file_size": 3072,
      "content_type": "video/mp4",
      "created": "2025-08-17T02:58:18.123456+00:00",
      "updated": "2025-08-17T02:58:18.123456+00:00"
    }
  ],
  "paging": {
    "limit": 100,
    "offset": 0,
    "total": 1
  }
}
```

**Status**: `200 OK`

---

### Step 6: Testing Segment Download

**Request:**
```http
GET http://localhost:8000/flows/0e9c9b8f-488f-4428-8867-2bc2550612c7/segments/550e8400-e29b-41d4-a716-446655440002/data
```

**Response:**
- **Status**: `200 OK`
- **Content-Type**: `video/mp4`
- **Content-Length**: `3072`
- **Body**: Binary video file content

---

### Step 7: Getting Presigned URL for Download

**Request:**
```http
GET http://localhost:8000/flows/0e9c9b8f-488f-4428-8867-2bc2550612c7/segments/550e8400-e29b-41d4-a716-446655440002/url
```

**Response:**
```json
{
  "url": "http://172.200.204.91/jthaloor-s3/tams/2025/08/17/0e9c9b8f-488f-4428-8867-2bc2550612c7/9e57802a-3e84-4f5c-943c-0a74fa1f1909.mp4?AWSAccessKeyId=SRSPW0DQT9T70Y787U68&Signature=...&Expires=1755403100",
  "expires_at": "2025-08-17T03:58:20+00:00",
  "operation": "get_object"
}
```

**Status**: `200 OK`

---

### Step 8: Testing Flow-Source Relationship

**Request:**
```http
GET http://localhost:8000/flows/0e9c9b8f-488f-4428-8867-2bc2550612c7
```

**Response:**
```json
{
  "id": "0e9c9b8f-488f-4428-8867-2bc2550612c7",
  "source_id": "32cffed8-2015-4e89-a2d7-4395b1b1c1f5",
  "format": "urn:x-nmos:format:video",
  "codec": "video/mp4",
  "label": "HTTP API Test Flow",
  "description": "Flow for testing HTTP API workflow",
  "frame_width": 1920,
  "frame_height": 1080,
  "frame_rate": "25/1",
  "read_only": false,
  "created": "2025-08-17T02:58:17.242588+00:00",
  "updated": "2025-08-17T02:58:17.242588+00:00",
  "tags": {},
  "flow_collection": null
}
```

**Status**: `200 OK`

---

### Step 9: Testing Source-Flow Relationship

**Request:**
```http
GET http://localhost:8000/sources/32cffed8-2015-4e89-a2d7-4395b1b1c1f5
```

**Response:**
```json
{
  "id": "32cffed8-2015-4e89-a2d7-4395b1b1c1f5",
  "format": "urn:x-nmos:format:video",
  "label": "HTTP API Test Source",
  "description": "Source for testing HTTP API workflow",
  "created": "2025-08-17T02:58:16.738844+00:00",
  "updated": "2025-08-17T02:58:16.738844+00:00",
  "tags": {},
  "source_collection": [],
  "collected_by": []
}
```

**Status**: `200 OK`

---

### Step 10: Testing Deletion Workflow

#### Step 10a: Delete Flow (Soft Delete)

**Request:**
```http
DELETE http://localhost:8000/flows/0e9c9b8f-488f-4428-8867-2bc2550612c7?soft_delete=true&cascade=true&deleted_by=test-user
```

**Response:**
- **Status**: `204 No Content`
- **Body**: No content

#### Step 10b: Verify Flow Deletion

**Request:**
```http
GET http://localhost:8000/flows/0e9c9b8f-488f-4428-8867-2bc2550612c7
```

**Response:**
- **Status**: `404 Not Found`
- **Body**: `{"detail": "Flow not found"}`

#### Step 10c: Verify Segments Deletion

**Request:**
```http
GET http://localhost:8000/flows/0e9c9b8f-488f-4428-8867-2bc2550612c7/segments
```

**Response:**
```json
{
  "data": [],
  "paging": {
    "limit": 100,
    "offset": 0,
    "total": 0
  }
}
```

**Status**: `200 OK`

#### Step 10d: Delete Source (Soft Delete)

**Request:**
```http
DELETE http://localhost:8000/sources/32cffed8-2015-4e89-a2d7-4395b1b1c1f5?soft_delete=true&cascade=true&deleted_by=test-user
```

**Response:**
- **Status**: `204 No Content`
- **Body**: No content

#### Step 10e: Verify Source Deletion

**Request:**
```http
GET http://localhost:8000/sources/32cffed8-2015-4e89-a2d7-4395b1b1c1f5
```

**Response:**
- **Status**: `404 Not Found`
- **Body**: `{"detail": "Source not found"}`

---

## Python Client Example

### Complete Python Workflow

```python
import requests
import json
import uuid
from pathlib import Path

class TAMSClient:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = requests.Session()
    
    def create_source(self, source_data: dict) -> dict:
        """Create a new media source"""
        response = self.session.post(
            f"{self.base_url}/sources",
            json=source_data
        )
        response.raise_for_status()
        return response.json()
    
    def create_flow(self, flow_data: dict) -> dict:
        """Create a new media flow"""
        response = self.session.post(
            f"{self.base_url}/flows",
            json=flow_data
        )
        response.raise_for_status()
        return response.json()
    
    def create_segment(self, flow_id: str, segment_data: dict, file_path: str) -> dict:
        """Create a new flow segment with file upload"""
        with open(file_path, 'rb') as f:
            files = {
                'segment': (None, json.dumps(segment_data), 'application/json'),
                'file': (Path(file_path).name, f, 'video/mp4')
            }
            response = self.session.post(
                f"{self.base_url}/flows/{flow_id}/segments",
                files=files
            )
        response.raise_for_status()
        return response.json()
    
    def get_segments(self, flow_id: str) -> dict:
        """Get all segments for a flow"""
        response = self.session.get(
            f"{self.base_url}/flows/{flow_id}/segments"
        )
        response.raise_for_status()
        return response.json()
    
    def delete_flow(self, flow_id: str, soft_delete: bool = True, cascade: bool = True) -> bool:
        """Delete a flow"""
        params = {
            'soft_delete': soft_delete,
            'cascade': cascade,
            'deleted_by': 'test-user'
        }
        response = self.session.delete(
            f"{self.base_url}/flows/{flow_id}",
            params=params
        )
        return response.status_code == 204
    
    def delete_source(self, source_id: str, soft_delete: bool = True, cascade: bool = True) -> bool:
        """Delete a source"""
        params = {
            'soft_delete': soft_delete,
            'cascade': cascade,
            'deleted_by': 'test-user'
        }
        response = self.session.delete(
            f"{self.base_url}/sources/{source_id}",
            params=params
        )
        return response.status_code == 204

# Usage example
def main():
    client = TAMSClient("http://localhost:8000")
    
    # Step 1: Create source
    source_data = {
        "id": str(uuid.uuid4()),
        "format": "urn:x-nmos:format:video",
        "label": "Test Source",
        "description": "Test source for workflow"
    }
    source = client.create_source(source_data)
    print(f"Created source: {source['id']}")
    
    # Step 2: Create flow
    flow_data = {
        "id": str(uuid.uuid4()),
        "source_id": source['id'],
        "format": "urn:x-nmos:format:video",
        "codec": "video/mp4",
        "frame_width": 1920,
        "frame_height": 1080,
        "frame_rate": "25/1",
        "label": "Test Flow",
        "description": "Test flow for workflow"
    }
    flow = client.create_flow(flow_data)
    print(f"Created flow: {flow['id']}")
    
    # Step 3: Create segment
    segment_data = {
        "object_id": str(uuid.uuid4()),
        "timerange": "[0:0_10:0)",
        "sample_offset": 0,
        "sample_count": 250
    }
    segment = client.create_segment(flow['id'], segment_data, "test_segment.mp4")
    print(f"Created segment: {segment['id']}")
    
    # Step 4: Verify segment
    segments = client.get_segments(flow['id'])
    print(f"Flow has {len(segments['data'])} segments")
    
    # Step 5: Cleanup
    client.delete_flow(flow['id'])
    client.delete_source(source['id'])
    print("Cleanup completed")

if __name__ == "__main__":
    main()
```

## cURL Examples

### Create Source
```bash
curl -X POST "http://localhost:8000/sources" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "32cffed8-2015-4e89-a2d7-4395b1b1c1f5",
    "format": "urn:x-nmos:format:video",
    "label": "Test Source",
    "description": "Test source for workflow"
  }'
```

### Create Flow
```bash
curl -X POST "http://localhost:8000/flows" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "0e9c9b8f-488f-4428-8867-2bc2550612c7",
    "source_id": "32cffed8-2015-4e89-a2d7-4395b1b1c1f5",
    "format": "urn:x-nmos:format:video",
    "codec": "video/mp4",
    "frame_width": 1920,
    "frame_height": 1080,
    "frame_rate": "25/1",
    "label": "Test Flow",
    "description": "Test flow for workflow"
  }'
```

### Create Segment with File Upload
```bash
curl -X POST "http://localhost:8000/flows/0e9c9b8f-488f-4428-8867-2bc2550612c7/segments" \
  -F "segment={\"object_id\":\"9e57802a-3e84-4f5c-943c-0a74fa1f1909\",\"timerange\":\"[0:0_10:0)\",\"sample_offset\":0,\"sample_count\":250}" \
  -F "file=@test_segment.mp4"
```

### Get Segments
```bash
curl "http://localhost:8000/flows/0e9c9b8f-488f-4428-8867-2bc2550612c7/segments"
```

### Delete Flow
```bash
curl -X DELETE "http://localhost:8000/flows/0e9c9b8f-488f-4428-8867-2bc2550612c7?soft_delete=true&cascade=true&deleted_by=test-user"
```

### Delete Source
```bash
curl -X DELETE "http://localhost:8000/sources/32cffed8-2015-4e89-a2d7-4395b1b1c1f5?soft_delete=true&cascade=true&deleted_by=test-user"
```

## Key Features Demonstrated

### 1. **Complete Lifecycle Management**
- Source creation and management
- Flow creation linked to sources
- Segment creation with file uploads
- Proper cleanup and deletion

### 2. **File Upload Integration**
- Multipart form data handling
- Automatic file storage organization
- File metadata management
- Content type detection

### 3. **Relationship Management**
- Source-Flow relationships
- Flow-Segment relationships
- Cascade deletion support
- Referential integrity

### 4. **Soft Delete Support**
- Configurable soft/hard delete
- Cascade delete options
- Audit trail with deleted_by
- Data recovery capabilities

### 5. **Storage Organization**
- Automatic date-based organization
- Flow-based file grouping
- Consistent storage paths
- S3-compatible storage

## Error Handling

### Common Error Scenarios

#### 1. **Invalid Source ID**
```json
{
  "detail": "Source not found"
}
```

#### 2. **Invalid Flow ID**
```json
{
  "detail": "Flow not found"
}
```

#### 3. **Validation Errors**
```json
{
  "detail": [
    {
      "loc": ["body", "format"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

#### 4. **File Upload Errors**
```json
{
  "detail": "File upload failed: Invalid file format"
}
```

## Best Practices

### 1. **ID Management**
- Use UUIDs for all resource IDs
- Ensure uniqueness across the system
- Validate ID format before API calls

### 2. **File Handling**
- Validate file types before upload
- Use appropriate content types
- Handle large files appropriately

### 3. **Error Handling**
- Always check HTTP status codes
- Implement retry logic for transient failures
- Log errors for debugging

### 4. **Cleanup**
- Always clean up test resources
- Use soft delete for data safety
- Implement proper cascade deletion

### 5. **Performance**
- Use pagination for large result sets
- Implement caching where appropriate
- Monitor API response times

## Testing Considerations

### 1. **Test Data Isolation**
- Use unique IDs for each test run
- Clean up all test resources
- Avoid conflicts between test runs

### 2. **File Management**
- Use small test files for quick testing
- Clean up uploaded files
- Test various file formats

### 3. **Error Scenarios**
- Test invalid IDs and references
- Test malformed requests
- Test network failures

### 4. **Performance Testing**
- Test with multiple concurrent requests
- Monitor response times
- Test with large datasets

This sample workflow demonstrates the complete TAMS API lifecycle, from creation through deletion, with proper error handling and best practices. The workflow can be used as a template for building more complex integrations and testing scenarios.
