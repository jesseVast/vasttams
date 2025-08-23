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
- **OpenAPI Specification**: `/openapi.json`

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
  "description": "Primary studio camera for live broadcasts"
}
```

**Expected Response (201 Created):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "format": "urn:x-nmos:format:video",
  "label": "Main Camera 1",
  "description": "Primary studio camera for live broadcasts",
  "created": "2024-12-20T10:00:00Z",
  "updated": "2024-12-20T10:00:00Z",
  "tags": {},
  "source_collection": [],
  "collected_by": []
}
```

### Reading Sources

#### List All Sources
```bash
GET /sources
```

**Query Parameters:**
- `limit` (optional): Number of results per page (default: 100)
- `offset` (optional): Number of results to skip (default: 0)
- `format` (optional): Filter by media format
- `label` (optional): Filter by label (partial match)

**Expected Response (200 OK):**
```json
{
  "data": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "format": "urn:x-nmos:format:video",
      "label": "Main Camera 1",
      "description": "Primary studio camera for live broadcasts",
      "created": "2024-12-20T10:00:00Z",
      "updated": "2024-12-20T10:00:00Z"
    },
    {
      "id": "550e8400-e29b-41d4-a716-446655440001",
      "format": "urn:x-nmos:format:video",
      "label": "Camera 2",
      "description": "Secondary camera angle",
      "created": "2024-12-20T10:00:00Z",
      "updated": "2024-12-20T10:00:00Z"
    }
  ],
  "paging": {
    "limit": 100,
    "offset": 0,
    "total": 2
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
  "created": "2024-12-20T10:00:00Z",
  "updated": "2024-12-20T10:00:00Z",
  "tags": {},
  "source_collection": [],
  "collected_by": []
}
```

#### Filter Sources
```bash
GET /sources?format=urn:x-nmos:format:video&label=Main Camera&limit=10&offset=0
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
    "limit": 10,
    "offset": 0,
    "total": 1
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
PUT /sources/{source_id}/tags/{tag_name}
```

**Request Body:**
```json
"tag_value"
```

**Expected Response (200 OK):**
```json
"tag_value"
```

### Deleting Sources

#### Delete Source
```bash
DELETE /sources/{source_id}
```

**Query Parameters:**
- `soft_delete` (optional): Perform soft delete (default: true)
- `cascade` (optional): Cascade delete to associated flows (default: true)
- `deleted_by` (optional): User/system performing deletion (default: "system")

**Expected Response (204 No Content):**
No response body

**Note**: This endpoint supports soft delete by default, which marks the source as deleted without removing it from the database. Use `soft_delete=false` for hard delete.

---

## 🌊 Flows Management

### Creating Flows

#### Create Single Flow
```bash
POST /flows
```

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
  "label": "HD Video Stream",
  "description": "High definition video stream from main camera"
}
```

**Expected Response (201 Created):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440001",
  "source_id": "550e8400-e29b-41d4-a716-446655440000",
  "format": "urn:x-nmos:format:video",
  "codec": "video/mp4",
  "frame_width": 1920,
  "frame_height": 1080,
  "frame_rate": "25/1",
  "label": "HD Video Stream",
  "description": "High definition video stream from main camera",
  "read_only": false,
  "created": "2024-12-20T10:00:00Z",
  "updated": "2024-12-20T10:00:00Z",
  "tags": {},
  "flow_collection": null
}
```

### Reading Flows

#### List All Flows
```bash
GET /flows
```

**Query Parameters:**
- `limit` (optional): Number of results per page (default: 100)
- `offset` (optional): Number of results to skip (default: 0)
- `source_id` (optional): Filter by source ID
- `format` (optional): Filter by media format
- `label` (optional): Filter by label (partial match)

**Expected Response (200 OK):**
```json
{
  "data": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440001",
      "source_id": "550e8400-e29b-41d4-a716-446655440000",
      "format": "urn:x-nmos:format:video",
      "codec": "video/mp4",
      "frame_width": 1920,
      "frame_height": 1080,
      "frame_rate": "25/1",
      "label": "HD Video Stream",
      "description": "High definition video stream from main camera",
      "read_only": false,
      "created": "2024-12-20T10:00:00Z",
      "updated": "2024-12-20T10:00:00Z"
    }
  ],
  "paging": {
    "limit": 100,
    "offset": 0,
    "total": 1
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
  "id": "550e8400-e29b-41d4-a716-446655440001",
  "source_id": "550e8400-e29b-41d4-a716-446655440000",
  "format": "urn:x-nmos:format:video",
  "codec": "video/mp4",
  "frame_width": 1920,
  "frame_height": 1080,
  "frame_rate": "25/1",
  "label": "HD Video Stream",
  "description": "High definition video stream from main camera",
  "read_only": false,
  "created": "2024-12-20T10:00:00Z",
  "updated": "2024-12-20T10:00:00Z",
  "tags": {},
  "flow_collection": null
}
```

### Updating Flows

#### Update Flow Description
```bash
PUT /flows/{flow_id}/description
```

**Request Body:**
```json
"Updated description for the HD video stream"
```

**Expected Response (200 OK):**
```json
"Updated description for the HD video stream"
```

#### Update Flow Label
```bash
PUT /flows/{flow_id}/label
```

**Request Body:**
```json
"HD Video Stream - Updated"
```

**Expected Response (200 OK):**
```json
"HD Video Stream - Updated"
```

#### Update Flow Tags
```bash
PUT /flows/{flow_id}/tags/{tag_name}
```

**Request Body:**
```json
"tag_value"
```

**Expected Response (200 OK):**
```json
"tag_value"
```

#### Update Flow Read-Only Status
```bash
PUT /flows/{flow_id}/read_only
```

**Request Body:**
```json
true
```

**Expected Response (200 OK):**
```json
true
```

### Deleting Flows

#### Delete Flow
```bash
DELETE /flows/{flow_id}
```

**Query Parameters:**
- `soft_delete` (optional): Perform soft delete (default: true)
- `cascade` (optional): Cascade delete to associated segments (default: true)
- `deleted_by` (optional): User/system performing deletion (default: "system")

**Expected Response (204 No Content):**
No response body

**Note**: This endpoint supports soft delete by default, which marks the flow as deleted without removing it from the database. Use `soft_delete=false` for hard delete.

---

## 📹 Flow Segments Management

### Creating Flow Segments

#### Upload Flow Segment
```bash
POST /flows/{flow_id}/segments
```

**Request Body (multipart/form-data):**
- `segment`: JSON string containing segment metadata
- `file`: Media file (video, audio, etc.)

**Segment Metadata Example:**
```json
{
  "object_id": "seg_001",
  "timerange": "[0:0_10:0)",
  "sample_offset": 0,
  "sample_count": 250
}
```

**Expected Response (201 Created):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440002",
  "flow_id": "550e8400-e29b-41d4-a716-446655440001",
  "object_id": "seg_001",
  "timerange": "[0:0_10:0)",
  "sample_offset": 0,
  "sample_count": 250,
  "storage_path": "tams/2024/12/20/550e8400-e29b-41d4-a716-446655440001/seg_001.mp4",
  "file_size": 1048576,
  "content_type": "video/mp4",
  "created": "2024-12-20T10:00:00Z",
  "updated": "2024-12-20T10:00:00Z"
}
```

### Reading Flow Segments

#### List Flow Segments
```bash
GET /flows/{flow_id}/segments
```

**Query Parameters:**
- `limit` (optional): Number of results per page (default: 100)
- `offset` (optional): Number of results to skip (default: 0)
- `timerange` (optional): Filter by time range
- `object_id` (optional): Filter by object ID

**Expected Response (200 OK):**
```json
{
  "data": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440002",
      "flow_id": "550e8400-e29b-41d4-a716-446655440001",
      "object_id": "seg_001",
      "timerange": "[0:0_10:0)",
      "sample_offset": 0,
      "sample_count": 250,
      "storage_path": "tams/2024/12/20/550e8400-e29b-41d4-a716-446655440001/seg_001.mp4",
      "file_size": 1048576,
      "content_type": "video/mp4",
      "created": "2024-12-20T10:00:00Z",
      "updated": "2024-12-20T10:00:00Z"
    }
  ],
  "paging": {
    "limit": 100,
    "offset": 0,
    "total": 1
  }
}
```

#### Get Flow Segment by ID
```bash
GET /flows/{flow_id}/segments/{segment_id}
```

**Expected Response (200 OK):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440002",
  "flow_id": "550e8400-e29b-41d4-a716-446655440001",
  "object_id": "seg_001",
  "timerange": "[0:0_10:0)",
  "sample_offset": 0,
  "sample_count": 250,
  "storage_path": "tams/2024/12/20/550e8400-e29b-41d4-a716-446655440001/seg_001.mp4",
  "file_size": 1048576,
  "content_type": "video/mp4",
  "created": "2024-12-20T10:00:00Z",
  "updated": "2024-12-20T10:00:00Z"
}
```

### Downloading Flow Segments

#### Download Flow Segment Data
```bash
GET /flows/{flow_id}/segments/{segment_id}/data
```

**Expected Response (200 OK):**
Binary file content with appropriate `Content-Type` header

#### Get Presigned URL for Download
```bash
GET /flows/{flow_id}/segments/{segment_id}/url
```

**Query Parameters:**
- `operation` (optional): Operation type (default: "get_object")
- `expires_in` (optional): URL expiration time in seconds (default: 3600)

**Expected Response (200 OK):**
```json
{
  "url": "https://your-s3-endpoint.com/bucket/path?X-Amz-Algorithm=...",
  "expires_at": "2024-12-20T11:00:00Z",
  "operation": "get_object"
}
```

### Deleting Flow Segments

#### Delete Flow Segments
```bash
DELETE /flows/{flow_id}/segments
```

**Query Parameters:**
- `timerange` (optional): Delete segments within specific time range
- `object_id` (optional): Delete specific segment by object ID
- `soft_delete` (optional): Perform soft delete (default: true)
- `deleted_by` (optional): User/system performing deletion (default: "system")

**Expected Response (204 No Content):**
No response body

---

## 🏷️ Tags Management

### Managing Source Tags

#### Get Source Tags
```bash
GET /sources/{source_id}/tags
```

**Expected Response (200 OK):**
```json
{
  "location": "studio-a",
  "quality": "hd",
  "camera_type": "panasonic"
}
```

#### Update Source Tag
```bash
PUT /sources/{source_id}/tags/{tag_name}
```

**Request Body:**
```json
"studio-b"
```

**Expected Response (200 OK):**
```json
"studio-b"
```

#### Delete Source Tag
```bash
DELETE /sources/{source_id}/tags/{tag_name}
```

**Expected Response (204 No Content):**
No response body

### Managing Flow Tags

#### Get Flow Tags
```bash
GET /flows/{flow_id}/tags
```

**Expected Response (200 OK):**
```json
{
  "quality": "hd",
  "codec": "h264",
  "bitrate": "high"
}
```

#### Update Flow Tag
```bash
PUT /flows/{flow_id}/tags/{tag_name}
```

**Request Body:**
```json
"ultra-hd"
```

**Expected Response (200 OK):**
```json
"ultra-hd"
```

#### Delete Flow Tag
```bash
DELETE /flows/{flow_id}/tags/{tag_name}
```

**Expected Response (204 No Content):**
No response body

---

## 📊 Analytics Endpoints

### Flow Usage Analytics
```bash
GET /analytics/flow-usage
```

**Expected Response (200 OK):**
```json
{
  "total_flows": 150,
  "format_distribution": {
    "urn:x-nmos:format:video": 120,
    "urn:x-nmos:format:audio": 25,
    "urn:x-nmos:format:data": 5
  },
  "codec_distribution": {
    "video/mp4": 80,
    "video/h264": 40,
    "audio/aac": 20,
    "audio/mp3": 5
  },
  "resolution_distribution": {
    "1920x1080": 60,
    "1280x720": 40,
    "3840x2160": 20
  },
  "created_last_30_days": 25,
  "updated_last_30_days": 45
}
```

### Storage Usage Analytics
```bash
GET /analytics/storage-usage
```

**Expected Response (200 OK):**
```json
{
  "total_storage_bytes": 1073741824000,
  "storage_by_format": {
    "urn:x-nmos:format:video": 858993459200,
    "urn:x-nmos:format:audio": 214748364800
  },
  "storage_by_flow": {
    "flow-1": 107374182400,
    "flow-2": 53687091200
  },
  "access_patterns": {
    "last_24_hours": 50,
    "last_7_days": 300,
    "last_30_days": 1200
  },
  "storage_growth_rate": "5.2%"
}
```

### Time Range Analysis
```bash
GET /analytics/time-range-analysis
```

**Expected Response (200 OK):**
```json
{
  "total_segments": 5000,
  "time_range_distribution": {
    "0-10s": 2000,
    "10-30s": 1500,
    "30-60s": 1000,
    "60s+": 500
  },
  "average_duration": "25.5s",
  "duration_percentiles": {
    "p25": "12.3s",
    "p50": "25.5s",
    "p75": "38.7s",
    "p90": "52.1s",
    "p95": "58.9s"
  },
  "temporal_patterns": {
    "hourly_distribution": {
      "00:00": 150,
      "01:00": 120,
      "02:00": 100
    },
    "daily_distribution": {
      "Monday": 800,
      "Tuesday": 850,
      "Wednesday": 900
    }
  }
}
```

---

## 🔧 Service Management

### Service Information
```bash
GET /service
```

**Expected Response (200 OK):**
```json
{
  "id": "tams-service",
  "name": "TAMS API Service",
  "version": "7.0",
  "description": "Time-addressable Media Store API",
  "capabilities": [
    "sources",
    "flows",
    "segments",
    "analytics",
    "tags"
  ],
  "storage_backends": [
    {
      "id": "vast-db",
      "type": "vast",
      "status": "healthy"
    },
    {
      "id": "s3-storage",
      "type": "s3",
      "status": "healthy"
    }
  ],
  "created": "2024-12-20T10:00:00Z",
  "updated": "2024-12-20T10:00:00Z"
}
```

### Health Check
```bash
GET /health
```

**Expected Response (200 OK):**
```json
{
  "status": "healthy",
  "timestamp": "2024-12-20T10:00:00Z",
  "version": "7.0",
  "uptime_seconds": 3600,
  "dependencies": {
    "vast_database": "healthy",
    "s3_storage": "healthy"
  }
}
```

### Metrics
```bash
GET /metrics
```

**Expected Response (200 OK):**
Prometheus-formatted metrics including:
- HTTP request counts and durations
- Business metrics (sources, flows, segments)
- System metrics (CPU, memory, storage)
- Custom application metrics

---

## 🚀 Advanced Usage Patterns

### Batch Operations

#### Batch Source Creation
```bash
# Create multiple sources in parallel
for source_data in sources_list:
    response = requests.post(f"{base_url}/sources", json=source_data)
    # Handle response
```

#### Batch Flow Creation
```bash
# Create flows for multiple sources
for source in sources:
    flow_data = {
        "id": f"flow-{source['id']}",
        "source_id": source['id'],
        "format": source['format'],
        "label": f"Flow for {source['label']}"
    }
    response = requests.post(f"{base_url}/flows", json=flow_data)
```

### Time Range Queries

#### Query Segments by Time Range
```bash
# Get segments within specific time range
timerange = "[2024-12-20T10:00:00Z_2024-12-20T11:00:00Z)"
response = requests.get(f"{base_url}/flows/{flow_id}/segments?timerange={timerange}")
```

#### Complex Time Range Filtering
```bash
# Get segments from last 24 hours
from datetime import datetime, timedelta
end_time = datetime.utcnow()
start_time = end_time - timedelta(hours=24)
timerange = f"[{start_time.isoformat()}_{end_time.isoformat()})"
response = requests.get(f"{base_url}/flows/{flow_id}/segments?timerange={timerange}")
```

### Tag-Based Filtering

#### Filter by Multiple Tags
```bash
# Get sources with specific tags
response = requests.get(f"{base_url}/sources?tags.location=studio-a&tags.quality=hd")
```

#### Tag-Based Analytics
```bash
# Analyze flows by tag combinations
flows = requests.get(f"{base_url}/flows").json()
hd_flows = [f for f in flows['data'] if f.get('tags', {}).get('quality') == 'hd']
```

### Error Handling

#### Handle API Errors
```python
import requests

try:
    response = requests.post(f"{base_url}/sources", json=source_data)
    response.raise_for_status()
    return response.json()
except requests.exceptions.HTTPError as e:
    if e.response.status_code == 409:
        print("Source already exists")
    elif e.response.status_code == 400:
        print("Invalid source data")
    else:
        print(f"Unexpected error: {e}")
except requests.exceptions.RequestException as e:
    print(f"Request failed: {e}")
```

#### Retry Logic
```python
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

session = requests.Session()
retry_strategy = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504]
)
adapter = HTTPAdapter(max_retries=retry_strategy)
session.mount("http://", adapter)
session.mount("https://", adapter)

response = session.post(f"{base_url}/sources", json=source_data)
```

---

## 📋 Best Practices

### Performance Optimization

1. **Use Pagination**: Always use `limit` and `offset` parameters for large datasets
2. **Batch Operations**: Group related operations to reduce API calls
3. **Efficient Filtering**: Use specific query parameters instead of fetching all data
4. **Connection Reuse**: Reuse HTTP connections for multiple requests

### Data Management

1. **Consistent IDs**: Use UUIDs or consistent naming conventions for IDs
2. **Tag Strategy**: Plan your tag structure for efficient filtering and analytics
3. **Time Ranges**: Use standardized time range formats for consistency
4. **Metadata**: Include relevant metadata for better search and organization

### Error Handling

1. **Check Status Codes**: Always verify HTTP status codes
2. **Handle Retries**: Implement retry logic for transient failures
3. **Log Errors**: Log detailed error information for debugging
4. **Graceful Degradation**: Handle partial failures gracefully

### Security

1. **API Keys**: Use API keys for authentication when available
2. **HTTPS**: Always use HTTPS in production
3. **Input Validation**: Validate all input data before sending
4. **Rate Limiting**: Respect rate limits and implement backoff strategies

---

## 🔍 Troubleshooting

### Common Issues

#### Connection Errors
```bash
# Check if service is running
curl http://localhost:8000/health

# Check network connectivity
telnet localhost 8000

# Verify firewall settings
sudo ufw status
```

#### Authentication Errors
```bash
# Check API key format
echo $API_KEY

# Verify permissions
curl -H "Authorization: Bearer $API_KEY" http://localhost:8000/sources
```

#### Data Validation Errors
```bash
# Check request format
curl -X POST http://localhost:8000/sources \
  -H "Content-Type: application/json" \
  -d '{"id": "test", "format": "urn:x-nmos:format:video"}'

# Validate JSON syntax
echo '{"id": "test"}' | python -m json.tool
```

### Debug Mode

#### Enable Debug Logging
```bash
# Set debug environment variable
export DEBUG=true
export LOG_LEVEL=DEBUG

# Restart service
docker-compose restart tams-api
# or
sudo systemctl restart tams-api
```

#### Check Logs
```bash
# View application logs
docker-compose logs -f tams-api

# Check system logs
journalctl -u tams-api -f

# Monitor real-time logs
tail -f /var/log/tams/app.log
```

---

## 📚 Additional Resources

### Documentation
- **API Reference**: Interactive documentation at `/docs`
- **OpenAPI Spec**: Machine-readable API specification at `/openapi.json`
- **Architecture**: System architecture documentation
- **Development**: Development and contribution guidelines

### Support
- **GitHub Issues**: Report bugs and request features
- **Community**: Join community discussions
- **Examples**: Check the `examples/` directory for code samples

### Tools
- **Postman Collection**: Import the provided Postman collection
- **cURL Examples**: Use the cURL examples in this guide
- **SDK**: Use the provided Python SDK for easier integration

This usage guide provides comprehensive examples and best practices for using the TAMS API. For the most up-to-date information, always refer to the interactive API documentation at `/docs`.
