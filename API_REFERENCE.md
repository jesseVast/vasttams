# TAMS API Reference

This document provides complete documentation for all TAMS API endpoints, including request/response formats, parameters, and examples.

## 📖 Table of Contents

- [Core TAMS Endpoints](#core-tams-endpoints)
- [Sources Management](#sources-management)
- [Flows Management](#flows-management)
- [Flow Segments](#flow-segments)
- [Segment Tagging (6.0p4+ Extension)](#segment-tagging-tams-60p4-extension)
- [Media Objects](#media-objects)
- [Analytics Endpoints](#analytics-endpoints)
- [Webhook Management](#webhook-management)
- [Management Endpoints](#management-endpoints)
- [Error Handling](#error-handling)
- [Response Formats](#response-formats)

## 🔧 Core TAMS Endpoints

### Service Information

#### `GET /` - List Root Endpoints
Returns a list of available paths from this API.

**Response:**
```json
[
  "service",
  "flows",
  "sources",
  "flow-delete-requests"
]
```

#### `HEAD /` - Root Endpoints Headers
Return root path headers.

**Response:** HTTP 200 with headers

#### `GET /health` - Health Check
Enhanced health check endpoint with system metrics and dependency status.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-08-23T14:30:00Z",
  "version": "6.0",
  "dependencies": {
    "vast_database": "healthy",
    "s3_storage": "healthy"
  },
  "metrics": {
    "uptime_seconds": 3600,
    "memory_usage_mb": 128,
    "cpu_usage_percent": 2.5
  }
}
```

#### `GET /openapi.json` - OpenAPI Specification
Returns the complete OpenAPI specification in JSON format.

**Response:** OpenAPI 3.1.0 specification JSON

#### `GET /docs` - Interactive Documentation
Swagger UI documentation interface.

#### `GET /redoc` - ReDoc Documentation
Alternative API documentation interface.

#### `GET /service` - Service Information
Provide information about the service, including the media store in use.

**Response:**
```json
{
  "name": "TAMS API",
  "version": "6.0",
  "description": "Time-addressable Media Store API",
  "media_store": {
    "type": "http_object_store",
    "endpoint": "http://s3.example.com",
    "bucket": "tams-bucket"
  },
  "capabilities": [
    "sources",
    "flows",
    "segments",
    "objects",
    "analytics",
    "webhooks"
  ]
}
```

#### `POST /service` - Update Service Configuration
Update service configuration (admin only).

**Request Body:**
```json
{
  "media_store": {
    "type": "http_object_store",
    "endpoint": "http://new-s3.example.com",
    "bucket": "new-tams-bucket"
  }
}
```

## 📹 Sources Management

### `GET /sources` - List Sources
List all sources with filtering and pagination.

**Query Parameters:**
- `limit` (integer): Maximum number of results (default: 100)
- `page` (string): Pagination token for next page
- `format` (string): Filter by content format
- `collection` (string): Filter by source collection
- `tags` (string): Comma-separated list of tag names to filter by

**Response:**
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "format": "urn:x-nmos:format:video",
    "label": "Main Camera Feed",
    "description": "Primary camera source for live broadcast",
    "created_by": "user123",
    "updated_by": "user123",
    "created": "2025-08-23T14:00:00Z",
    "updated": "2025-08-23T14:00:00Z",
    "tags": {
      "location": "studio-a",
      "quality": "hd"
    },
    "source_collection": "main-cameras",
    "collected_by": "camera-system-1"
  }
]
```

**Headers:**
- `Link`: Pagination links for next/previous pages
- `X-Paging-NextKey`: Token for next page

### `POST /sources` - Create Source
Create a new media source.

**Request Body:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "format": "urn:x-nmos:format:video",
  "label": "Main Camera Feed",
  "description": "Primary camera source for live broadcast",
  "tags": {
    "location": "studio-a",
    "quality": "hd"
  },
  "source_collection": "main-cameras",
  "collected_by": "camera-system-1"
}
```

**Response:** HTTP 201 with created source

### `GET /sources/{id}` - Get Source
Get source by ID.

**Path Parameters:**
- `id` (string): Source UUID

**Response:** Source object

### `PUT /sources/{id}` - Update Source
Update source metadata.

**Path Parameters:**
- `id` (string): Source UUID

**Request Body:** Partial source object

**Response:** Updated source object

### `DELETE /sources/{id}` - Delete Source
Delete a source (soft delete by default).

**Path Parameters:**
- `id` (string): Source UUID

**Query Parameters:**
- `soft_delete` (boolean): Perform soft delete (default: true)
- `cascade` (boolean): Cascade delete to flows and segments (default: true)
- `deleted_by` (string): User performing deletion (default: "system")

**Response:** HTTP 204 No Content

### Source Tags Management

#### `GET /sources/{id}/tags` - Get Source Tags
Get all tags for a source.

**Response:**
```json
{
  "location": "studio-a",
  "quality": "hd",
  "camera_type": "panasonic"
}
```

#### `PUT /sources/{id}/tags/{name}` - Update Source Tag
Update a specific tag value.

**Path Parameters:**
- `id` (string): Source UUID
- `name` (string): Tag name

**Request Body:**
```json
"new-value"
```

**Response:** Updated tag value

#### `DELETE /sources/{id}/tags/{name}` - Delete Source Tag
Delete a specific tag.

**Path Parameters:**
- `id` (string): Source UUID
- `name` (string): Tag name

**Response:** HTTP 204 No Content

### Source Description Management

#### `GET /sources/{id}/description` - Get Source Description
Get source description.

**Response:**
```json
"Primary camera source for live broadcast"
```

#### `PUT /sources/{id}/description` - Update Source Description
Update source description.

**Request Body:**
```json
"Updated description text"
```

**Response:** Updated description

### Source Label Management

#### `GET /sources/{id}/label` - Get Source Label
Get source label.

**Response:**
```json
"Main Camera Feed"
```

#### `PUT /sources/{id}/label` - Update Source Label
Update source label.

**Request Body:**
```json
"Updated Label"
```

**Response:** Updated label

## 🎬 Flows Management

### `GET /flows` - List Flows
List all flows with filtering and pagination.

**Query Parameters:**
- `limit` (integer): Maximum number of results (default: 100)
- `page` (string): Pagination token for next page
- `source_id` (string): Filter by source ID
- `format` (string): Filter by content format
- `collection` (string): Filter by flow collection
- `tags` (string): Comma-separated list of tag names to filter by

**Response:**
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440001",
    "source_id": "550e8400-e29b-41d4-a716-446655440000",
    "format": "urn:x-nmos:format:video",
    "codec": "video/mp4",
    "label": "HD Video Stream",
    "description": "High definition video stream",
    "created_by": "user123",
    "updated_by": "user123",
    "created": "2025-08-23T14:00:00Z",
    "updated": "2025-08-23T14:00:00Z",
    "tags": {
      "quality": "hd",
      "resolution": "1920x1080"
    },
    "container": "mp4",
    "read_only": false,
    "frame_width": 1920,
    "frame_height": 1080,
    "frame_rate": "25/1",
    "interlace_mode": "progressive",
    "color_sampling": "4:2:0",
    "color_space": "bt709",
    "transfer_characteristics": "bt709",
    "color_primaries": "bt709"
  }
]
```

### `POST /flows` - Create Flow
Create a new media flow.

**Request Body:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440001",
  "source_id": "550e8400-e29b-41d4-a716-446655440000",
  "format": "urn:x-nmos:format:video",
  "codec": "video/mp4",
  "frame_width": 1920,
  "frame_height": 1080,
  "frame_rate": "25/1",
  "label": "HD Video Stream"
}
```

**Response:** HTTP 201 with created flow

### `GET /flows/{id}` - Get Flow
Get flow by ID.

**Path Parameters:**
- `id` (string): Flow UUID

**Response:** Flow object

### `PUT /flows/{id}` - Update Flow
Update flow metadata.

**Path Parameters:**
- `id` (string): Flow UUID

**Request Body:** Partial flow object

**Response:** Updated flow object

### `DELETE /flows/{id}` - Delete Flow
Delete a flow (soft delete by default).

**Path Parameters:**
- `id` (string): Flow UUID

**Query Parameters:**
- `soft_delete` (boolean): Perform soft delete (default: true)
- `cascade` (boolean): Cascade delete to segments (default: true)
- `deleted_by` (string): User performing deletion (default: "system")

**Response:** HTTP 204 No Content

### Flow Tags Management

#### `GET /flows/{id}/tags` - Get Flow Tags
Get all tags for a flow.

#### `PUT /flows/{id}/tags/{name}` - Update Flow Tag
Update a specific tag value.

#### `DELETE /flows/{id}/tags/{name}` - Delete Flow Tag
Delete a specific tag.

### Flow Description Management

#### `GET /flows/{id}/description` - Get Flow Description
Get flow description.

#### `PUT /flows/{id}/description` - Update Flow Description
Update flow description.

### Flow Label Management

#### `GET /flows/{id}/label` - Get Flow Label
Get flow label.

#### `PUT /flows/{id}/label` - Update Flow Label
Update flow label.

### Flow Read-Only Management

#### `GET /flows/{id}/read_only` - Get Flow Read-Only Status
Get flow read-only status.

**Response:**
```json
false
```

#### `PUT /flows/{id}/read_only` - Update Flow Read-Only Status
Update flow read-only status.

**Request Body:**
```json
true
```

**Response:** Updated read-only status

### Flow Collection Management

#### `GET /flows/{id}/flow_collection` - Get Flow Collection
Get flow collection (MultiFlow).

**Response:**
```json
"main-broadcast"
```

#### `PUT /flows/{id}/flow_collection` - Update Flow Collection
Update flow collection.

**Request Body:**
```json
"updated-collection"
```

**Response:** Updated collection

#### `DELETE /flows/{id}/flow_collection` - Delete Flow Collection
Delete flow collection.

**Response:** HTTP 204 No Content

## 📹 Flow Segments

### `GET /flows/{id}/segments` - Get Flow Segments
Get flow segments with time range filtering.

**Path Parameters:**
- `id` (string): Flow UUID

**Query Parameters:**
- `timerange` (string): Filter by time range (ISO 8601 format)
- `limit` (integer): Maximum number of results (default: 100)
- `page` (string): Pagination token for next page
- `accept_get_urls` (string): Comma-separated list of URL labels to include

**Response:**
```json
[
  {
    "object_id": "segment-123",
    "timerange": "2025-08-23T14:00:00Z/2025-08-23T14:05:00Z",
    "ts_offset": "PT0S",
    "last_duration": "PT5M",
    "sample_offset": 0,
    "sample_count": 7500,
    "key_frame_count": 125,
    "get_urls": [
      {
        "url": "http://s3.example.com/...",
        "label": "GET access for segment segment-123"
      },
      {
        "url": "http://s3.example.com/...",
        "label": "HEAD access for segment segment-123"
      }
    ]
  }
]
```

### `POST /flows/{id}/segments` - Create Flow Segment
Create flow segment (upload media data).

**Path Parameters:**
- `id` (string): Flow UUID

**Request Body:** Multipart form data
- `segment_data` (string): JSON string with segment metadata
- `file` (file, optional): Media file content

**Segment Data Format:**
```json
{
  "object_id": "seg_001",
  "timerange": "2025-08-23T14:00:00Z/2025-08-23T14:05:00Z",
  "ts_offset": "PT0S",
  "last_duration": "PT5M",
  "sample_offset": 0,
  "sample_count": 7500,
  "key_frame_count": 125
}
```

**Response:** HTTP 201 with created segment

### `DELETE /flows/{id}/segments` - Delete Flow Segments
Delete flow segments.

**Path Parameters:**
- `id` (string): Flow UUID

**Query Parameters:**
- `timerange` (string): Time range for deletion (ISO 8601 format)
- `soft_delete` (boolean): Perform soft delete (default: true)
- `deleted_by` (string): User performing deletion (default: "system")

**Response:** HTTP 204 No Content

### `POST /flows/{id}/storage` - Allocate Storage
Allocate storage for flow segments.

**Path Parameters:**
- `id` (string): Flow UUID

**Request Body:**
```json
{
  "timerange": "2025-08-23T14:00:00Z/2025-08-23T14:30:00Z",
  "size_bytes": 1048576
}
```

**Response:** HTTP 201 with storage allocation

### Segment Tagging (TAMS 6.0p4+ Extension)

> **⚠️ Note**: Segment tagging endpoints are **not part of the official 6.0 API specification**. These are TAMS-specific extensions available in release 6.0p4 and later.

#### `GET /flows/{flow_id}/segments/{segment_id}/tags` - Get Segment Tags
Get all tags for a specific segment.

**Path Parameters:**
- `flow_id` (string): Flow UUID
- `segment_id` (string): Segment ID (object_id)

**Response:**
```json
{
  "quality": "high",
  "type": "video",
  "resolution": "1080p"
}
```

#### `GET /flows/{flow_id}/segments/{segment_id}/tags/{name}` - Get Specific Tag
Get a specific tag value for a segment.

**Path Parameters:**
- `flow_id` (string): Flow UUID
- `segment_id` (string): Segment ID (object_id)
- `name` (string): Tag name

**Response:**
```json
{
  "quality": "high"
}
```

#### `PUT /flows/{flow_id}/segments/{segment_id}/tags/{name}` - Create/Update Tag
Create or update a tag for a segment.

**Path Parameters:**
- `flow_id` (string): Flow UUID
- `segment_id` (string): Segment ID (object_id)
- `name` (string): Tag name

**Request Body:**
```json
"high"
```

**Response:**
```json
{
  "message": "Tag updated successfully"
}
```

#### `DELETE /flows/{flow_id}/segments/{segment_id}/tags/{name}` - Delete Specific Tag
Delete a specific tag from a segment.

**Path Parameters:**
- `flow_id` (string): Flow UUID
- `segment_id` (string): Segment ID (object_id)
- `name` (string): Tag name

**Response:**
```json
{
  "message": "Tag deleted successfully"
}
```

#### `DELETE /flows/{flow_id}/segments/{segment_id}/tags` - Delete All Tags
Delete all tags for a segment.

**Path Parameters:**
- `flow_id` (string): Flow UUID
- `segment_id` (string): Segment ID (object_id)

**Response:**
```json
{
  "message": "All tags deleted successfully"
}
```

## 📦 Media Objects

### `GET /objects/{id}` - Get Media Object
Get media object details.

**Path Parameters:**
- `id` (string): Object ID

**Response:**
```json
{
  "object_id": "my-video-clip",
  "flow_references": [
    {
      "flow_id": "550e8400-e29b-41d4-a716-446655440001",
      "timerange": "2025-08-23T10:00:00Z/2025-08-23T10:05:00Z"
    }
  ],
  "size": 2668,
  "created": "2025-08-23T22:05:19.862893",
  "last_accessed": "2025-08-23T22:10:00.000000",
  "access_count": 5
}
```

### `POST /objects` - Create Media Object
Create media object (optional, objects created automatically with segments).

**Request Body:**
```json
{
  "object_id": "pre-created-object",
  "flow_references": [],
  "size": 0,
  "created": null
}
```

**Response:** HTTP 201 with created object

### `DELETE /objects/{id}` - Delete Media Object
Delete media object.

**Path Parameters:**
- `id` (string): Object ID

**Query Parameters:**
- `soft_delete` (boolean): Perform soft delete (default: true)
- `deleted_by` (string): User performing deletion (default: "system")

**Response:** HTTP 204 No Content

## 📊 Analytics Endpoints

### `GET /analytics/flow-usage` - Flow Usage Analytics
Get flow usage statistics and format distribution.

**Response:**
```json
{
  "total_flows": 150,
  "format_distribution": {
    "urn:x-nmos:format:video": 120,
    "urn:x-nmos:format:audio": 25,
    "urn:x-nmos:format:data": 5
  },
  "resolution_distribution": {
    "1920x1080": 80,
    "1280x720": 30,
    "3840x2160": 10
  },
  "codec_distribution": {
    "video/mp4": 90,
    "video/h264": 20,
    "video/h265": 10
  }
}
```

### `GET /analytics/storage-usage` - Storage Usage Analytics
Get storage usage analysis and access patterns.

**Response:**
```json
{
  "total_objects": 1250,
  "total_size_bytes": 1073741824,
  "size_distribution": {
    "small": 800,
    "medium": 300,
    "large": 150
  },
  "access_patterns": {
    "frequently_accessed": 200,
    "moderately_accessed": 500,
    "rarely_accessed": 550
  },
  "storage_efficiency": 0.85
}
```

### `GET /analytics/time-range-analysis` - Time Range Analysis
Get time range patterns and duration analysis.

**Response:**
```json
{
  "total_segments": 5000,
  "average_duration_seconds": 300,
  "duration_distribution": {
    "short": 2000,
    "medium": 2500,
    "long": 500
  },
  "time_coverage": {
    "start_date": "2025-01-01T00:00:00Z",
    "end_date": "2025-08-23T23:59:59Z",
    "total_coverage_hours": 5760
  }
}
```

## 🔔 Webhook Management

### `GET /service/webhooks` - List Webhooks
List registered webhooks.

**Response:**
```json
[
  {
    "id": "webhook-123",
    "url": "https://webhook.example.com/events",
    "api_key_name": "X-API-Key",
    "api_key_value": "***",
    "events": ["flows/segments_added"],
    "owner_id": "user123",
    "created_by": "user123",
    "created": "2025-08-23T14:00:00Z",
    "updated": "2025-08-23T14:00:00Z"
  }
]
```

### `POST /service/webhooks` - Create Webhook
Create new webhook for event notifications.

**Request Body:**
```json
{
  "url": "https://webhook.example.com/events",
  "api_key_name": "X-API-Key",
  "api_key_value": "your-webhook-secret",
  "events": ["flows/segments_added"],
  "owner_id": "user123",
  "created_by": "user123"
}
```

**Response:** HTTP 201 with created webhook

### `HEAD /service/webhooks` - Get Webhook Headers
Get webhook headers.

**Response:** HTTP 200 with headers

### `DELETE /service/webhooks/{id}` - Delete Webhook
Delete a webhook.

**Path Parameters:**
- `id` (string): Webhook UUID

**Response:** HTTP 204 No Content

## 🛠️ Management Endpoints

### `GET /flow-delete-requests` - List Deletion Requests
List all deletion requests.

**Query Parameters:**
- `status` (string): Filter by status
- `flow_id` (string): Filter by flow ID
- `limit` (integer): Maximum number of results
- `page` (string): Pagination token

**Response:**
```json
[
  {
    "id": "delete-request-123",
    "flow_id": "550e8400-e29b-41d4-a716-446655440001",
    "timerange": "2025-08-23T14:00:00Z/2025-08-23T14:30:00Z",
    "status": "completed",
    "created": "2025-08-23T14:00:00Z",
    "updated": "2025-08-23T14:05:00Z"
  }
]
```

### `POST /flow-delete-requests` - Create Deletion Request
Create a new deletion request.

**Request Body:**
```json
{
  "flow_id": "550e8400-e29b-41d4-a716-446655440001",
  "timerange": "2025-08-23T14:00:00Z/2025-08-23T14:30:00Z"
}
```

**Response:** HTTP 201 with created deletion request

### `GET /flow-delete-requests/{id}` - Get Deletion Request
Get deletion request by ID.

**Path Parameters:**
- `id` (string): Deletion request UUID

**Response:** Deletion request object

## ⚠️ Error Handling

### Error Response Format

All API errors follow a consistent format:

```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "segment_data", "timerange"],
      "msg": "Field required",
      "input": {
        "object_id": "seg_001"
      }
    }
  ]
}
```

### HTTP Status Codes

- **200 OK**: Request successful
- **201 Created**: Resource created successfully
- **204 No Content**: Request successful, no content returned
- **400 Bad Request**: Invalid request parameters
- **401 Unauthorized**: Authentication required
- **403 Forbidden**: Access denied
- **404 Not Found**: Resource not found
- **422 Unprocessable Entity**: Validation error
- **500 Internal Server Error**: Server error

### Common Error Scenarios

#### Validation Errors (422)
```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "timerange"],
      "msg": "Invalid time range format",
      "input": "invalid-format"
    }
  ]
}
```

#### Not Found Errors (404)
```json
{
  "detail": "Flow not found"
}
```

#### Bad Request Errors (400)
```json
{
  "detail": "Invalid query parameters"
}
```

## 📋 Response Formats

### Pagination

List endpoints support pagination with the following headers:

- `Link`: Pagination links for next/previous pages
- `X-Paging-NextKey`: Token for next page
- `X-Total-Count`: Total number of results

**Example Link Header:**
```
Link: <http://localhost:8000/flows?page=next-token>; rel="next"
```

### Content Negotiation

The API supports multiple response formats:

- **JSON**: Default format for all endpoints
- **OpenAPI**: Available at `/openapi.json`
- **Interactive Docs**: Available at `/docs` (Swagger UI)
- **ReDoc**: Available at `/redoc`

### Response Headers

All responses include standard headers:

- `Content-Type: application/json`
- `Cache-Control: no-cache`
- `X-Request-ID`: Unique request identifier for tracing
- `X-Response-Time`: Response time in milliseconds

## 🔐 Authentication & Authorization

### Current Implementation

- **No User Authentication**: OAuth2/JWT not implemented
- **API Key Authentication**: Webhook endpoints use API key authentication
- **Database Authentication**: VAST database access with access key/secret
- **S3 Authentication**: S3 operations with access key/secret

### Future Enhancements

- **OAuth2/JWT**: User authentication and authorization
- **RBAC**: Role-based access control
- **API Keys**: Per-user API key management
- **Rate Limiting**: Request rate limiting per user

## 📚 Additional Resources

- **[Usage Guide](USAGE.md)** - Comprehensive usage examples and patterns
- **[Architecture Guide](ARCHITECTURE.md)** - Technical architecture details
- **[Interactive API Docs](http://localhost:8000/docs)** - Swagger UI documentation
- **[ReDoc Documentation](http://localhost:8000/redoc)** - Alternative API documentation
- **[OpenAPI Specification](http://localhost:8000/openapi.json)** - Raw OpenAPI specification
