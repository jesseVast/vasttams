# TAMS API Usage Guide

This guide provides comprehensive examples and patterns for using the TAMS API, including detailed information about media segments, URL types, and common workflows.

## 📖 Table of Contents

- [Media Segments and URLs](#media-segments-and-urls)
- [Basic API Usage](#basic-api-usage)
- [Flow Segment Management](#flow-segment-management)
- [Object Management](#object-management)
- [Advanced Workflows](#advanced-workflows)
- [Error Handling](#error-handling)
- [Best Practices](#best-practices)

## 🔑 Media Segments and URLs

### Understanding URL Types

TAMS uses a segment-based approach where media content is divided into time-based segments. Each segment provides **two types of URLs** for different operations:

#### **GET URLs** - Data Retrieval
- **Purpose**: Download or stream the actual media content
- **Operation**: HTTP GET request
- **Response**: Binary media data (video, audio, etc.)
- **Use Case**: Media playback, content delivery, file downloads
- **Example**: Download a video segment for playback

#### **HEAD URLs** - Metadata Retrieval
- **Purpose**: Get metadata about the media segment without downloading content
- **Operation**: HTTP HEAD request
- **Response**: HTTP headers with metadata (file size, content type, etc.)
- **Use Case**: File information, size checking, content type verification
- **Example**: Check file size before deciding to download

### Fetching Segment URLs

To get the URLs for a segment:

```bash
# Get all segments for a flow
curl "http://localhost:8000/flows/{flow_id}/segments"

# Response includes get_urls array with both URL types:
{
  "object_id": "segment-123",
  "timerange": "2025-08-23T14:00:00Z/2025-08-23T14:05:00Z",
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
```

### Using the URLs

```bash
# Download media content (GET)
curl -O "$(curl -s 'http://localhost:8000/flows/{flow_id}/segments' | jq -r '.[0].get_urls[] | select(.label | contains("GET")) | .url')"

# Get metadata only (HEAD)
curl -I "$(curl -s 'http://localhost:8000/flows/{flow_id}/segments' | jq -r '.[0].get_urls[] | select(.label | contains("HEAD")) | .url')"

# Extract specific URL types programmatically
GET_URL=$(curl -s 'http://localhost:8000/flows/{flow_id}/segments' | jq -r '.[0].get_urls[] | select(.label | contains("GET")) | .url')
HEAD_URL=$(curl -s 'http://localhost:8000/flows/{flow_id}/segments' | jq -r '.[0].get_urls[] | select(.label | contains("HEAD")) | .url')

echo "GET URL: $GET_URL"
echo "HEAD URL: $HEAD_URL"
```

### URL Features

- **Pre-signed URLs**: Both URL types are pre-signed for secure access
- **Time-limited**: URLs expire after a configurable time (default: 1 hour)
- **No Extra Headers**: URLs work directly without additional authentication
- **S3 Compatible**: Works with any S3-compatible storage backend
- **Operation Specific**: Each URL is optimized for its specific HTTP operation

## 🚀 Basic API Usage

### Create a Video Source

```bash
curl -X POST "http://localhost:8000/sources" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "format": "urn:x-nmos:format:video",
    "label": "Main Camera Feed",
    "description": "Primary camera source for live broadcast",
    "tags": {
      "location": "studio-a",
      "quality": "hd"
    }
  }'
```

### Create a Video Flow

```bash
curl -X POST "http://localhost:8000/flows" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "550e8400-e29b-41d4-a716-446655440001",
    "source_id": "550e8400-e29b-41d4-a716-446655440000",
    "format": "urn:x-nmos:format:video",
    "codec": "video/mp4",
    "frame_width": 1920,
    "frame_height": 1080,
    "frame_rate": "25/1",
    "label": "HD Video Stream"
  }'
```

### Create Audio and Data Flows

```bash
# Audio Flow
curl -X POST "http://localhost:8000/flows" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "550e8400-e29b-41d4-a716-446655440002",
    "source_id": "550e8400-e29b-41d4-a716-446655440000",
    "format": "urn:x-nmos:format:audio",
    "codec": "audio/aac",
    "sample_rate": 48000,
    "bits_per_sample": 16,
    "channels": 2,
    "label": "Stereo Audio Stream"
  }'

# Data Flow
curl -X POST "http://localhost:8000/flows" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "550e8400-e29b-41d4-a716-446655440003",
    "source_id": "550e8400-e29b-41d4-a716-446655440000",
    "format": "urn:x-nmos:format:data",
    "codec": "application/json",
    "label": "Metadata Stream"
  }'
```

## 📹 Flow Segment Management

### Creating Segments

The API supports multiple ways to create segments:

#### **1. Upload Segment with Media File (Multipart Form) - ✅ RECOMMENDED**

```bash
curl -X POST "http://localhost:8000/flows/550e8400-e29b-41d4-a716-446655440001/segments" \
  -F "segment_data={\"object_id\":\"seg_001\",\"timerange\":\"2025-08-23T14:00:00Z/2025-08-23T14:05:00Z\",\"ts_offset\":\"PT0S\",\"last_duration\":\"PT5M\",\"sample_offset\":0,\"sample_count\":7500,\"key_frame_count\":125}" \
  -F "file=@video_segment.mp4"
```

#### **2. Create Segment with Form Data Only (No File) - ✅ WORKING**

```bash
curl -X POST "http://localhost:8000/flows/550e8400-e29b-41d4-a716-446655440001/segments" \
  -F "segment_data={\"object_id\":\"seg_003\",\"timerange\":\"2025-08-23T14:10:00Z/2025-08-23T14:15:00Z\"}"
```

#### **3. Create Segment with JSON Data Only - ⚠️ CURRENTLY NOT WORKING**

```bash
curl -X POST "http://localhost:8000/flows/550e8400-e29b-41d4-a716-446655440001/segments" \
  -H "Content-Type: application/json" \
  -d '{
    "object_id": "seg_002",
    "timerange": "2025-08-23T14:05:00Z/2025-08-23T14:10:00Z",
    "ts_offset": "PT0S",
    "last_duration": "PT5M",
    "sample_offset": 0,
    "sample_count": 7500,
    "key_frame_count": 125
  }'
```

**Note**: JSON-only requests are currently not working due to a FastAPI parameter binding issue. Use multipart form or form-only methods instead.

### Segment Field Requirements

**Required Fields:**
- `object_id`: Unique identifier for the segment
- `timerange`: ISO 8601 time range (e.g., "2025-08-23T14:00:00Z/2025-08-23T14:05:00Z")

**Optional Fields:**
- `ts_offset`: Timestamp offset (e.g., "PT0S")
- `last_duration`: Duration of the segment (e.g., "PT5M")
- `sample_offset`: Starting sample offset
- `sample_count`: Number of samples in the segment
- `key_frame_count`: Number of key frames

**Notes:**
- **Multipart Form**: Use `segment_data` field for JSON metadata + `file` field for media content
- **Form Only**: Use `segment_data` field for metadata without media file
- **Timerange Format**: Use ISO 8601 format (e.g., "2025-08-23T14:00:00Z/2025-08-23T14:05:00Z")

### Retrieving Segments

```bash
# Get all segments for a flow
curl "http://localhost:8000/flows/550e8400-e29b-41d4-a716-446655440001/segments"

# Get segments with time range filtering
curl "http://localhost:8000/flows/550e8400-e29b-41d4-a716-446655440001/segments?timerange=2025-08-23T14:00:00Z/2025-08-23T14:30:00Z"

# Get segments with pagination
curl "http://localhost:8000/flows/550e8400-e29b-41d4-a716-446655440001/segments?limit=10&page=1"
```

### Segment Response Structure

```json
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
  ],
  "deleted": false,
  "deleted_at": null,
  "deleted_by": null
}
```

## 🔄 Object Management

### Creating Objects

#### **Create Object Directly (Optional)**

```bash
curl -X POST "http://localhost:8000/objects" \
  -H "Content-Type: application/json" \
  -d '{
    "object_id": "pre-created-object",
    "flow_references": [],
    "size": 0,
    "created": null
  }'
```

#### **Automatic Object Creation**

Objects are automatically created when first referenced in segments:

```bash
# This will automatically create the object "auto-object-123"
curl -X POST "http://localhost:8000/flows/550e8400-e29b-41d4-a716-446655440001/segments" \
  -F "segment_data={\"object_id\":\"auto-object-123\",\"timerange\":\"2025-08-23T22:00:00Z/2025-08-23T22:05:00Z\"}"
```

### Managing Objects

#### **Check Object Details**

```bash
curl -X GET "http://localhost:8000/objects/my-video-clip" | jq .
```

#### **View Object Flow References**

The response will show all segments that reference this object:

```json
{
  "object_id": "my-video-clip",
  "flow_references": [
    {
      "flow_id": "550e8400-e29b-41d4-a716-446655440001",
      "timerange": "2025-08-23T10:00:00Z/2025-08-23T10:05:00Z"
    },
    {
      "flow_id": "550e8400-e29b-41d4-a716-446655440001",
      "timerange": "2025-08-23T15:00:00Z/2025-08-23T15:05:00Z"
    },
    {
      "flow_id": "550e8400-e29b-41d4-a716-446655440001",
      "timerange": "2025-08-23T20:00:00Z/2025-08-23T20:10:00Z"
    }
  ],
  "size": 2668,
  "created": "2025-08-23T22:05:19.862893",
  "deleted": false
}
```

#### **Delete Object**

```bash
# Soft delete (default)
curl -X DELETE "http://localhost:8000/objects/my-video-clip?soft_delete=true&deleted_by=user123"

# Hard delete (removes from database)
curl -X DELETE "http://localhost:8000/objects/my-video-clip?soft_delete=false&deleted_by=admin"
```

## 🔄 Advanced Workflows

### Object Reuse Across Multiple Timeranges

You can create multiple segments that reference the same object ID across different time ranges:

#### **Reuse Existing Object with Different Timerange**

```bash
# First segment (creates object)
curl -X POST "http://localhost:8000/flows/550e8400-e29b-41d4-a716-446655440001/segments" \
  -F "segment_data={\"object_id\":\"my-video-clip\",\"timerange\":\"2025-08-23T10:00:00Z/2025-08-23T10:05:00Z\"}" \
  -F "file=@video_clip.mp4"

# Second segment (same object, different time)
curl -X POST "http://localhost:8000/flows/550e8400-e29b-41d4-a716-446655440001/segments" \
  -F "segment_data={\"object_id\":\"my-video-clip\",\"timerange\":\"2025-08-23T15:00:00Z/2025-08-23T15:05:00Z\"}" \
  -F "file=@video_clip.mp4"

# Third segment (same object, no file - metadata only)
curl -X POST "http://localhost:8000/flows/550e8400-e29b-41d4-a716-446655440001/segments" \
  -F "segment_data={\"object_id\":\"my-video-clip\",\"timerange\":\"2025-08-23T20:00:00Z/2025-08-23T20:10:00Z\"}"
```

#### **Reference Non-Existent Object (Auto-Created)**

```bash
# Object will be automatically created when first referenced
curl -X POST "http://localhost:8000/flows/550e8400-e29b-41d4-a716-446655440001/segments" \
  -F "segment_data={\"object_id\":\"future-object-123\",\"timerange\":\"2025-08-23T22:00:00Z/2025-08-23T22:05:00Z\"}"
```

### Complete Workflow Example

Here's a complete example of creating and reusing objects:

```bash
# Step 1: Create first segment (creates object automatically)
curl -X POST "http://localhost:8000/flows/550e8400-e29b-41d4-a716-446655440001/segments" \
  -F "segment_data={\"object_id\":\"demo-video\",\"timerange\":\"2025-08-23T09:00:00Z/2025-08-23T09:02:00Z\"}" \
  -F "file=@demo_video.mp4"

# Step 2: Create second segment (same object, different time)
curl -X POST "http://localhost:8000/flows/550e8400-e29b-41d4-a716-446655440001/segments" \
  -F "segment_data={\"object_id\":\"demo-video\",\"timerange\":\"2025-08-23T14:00:00Z/2025-08-23T14:02:00Z\"}" \
  -F "file=@demo_video.mp4"

# Step 3: Check object details
curl -X GET "http://localhost:8000/objects/demo-video" | jq .

# Step 4: Create metadata-only segment (same object, no file)
curl -X POST "http://localhost:8000/flows/550e8400-e29b-41d4-a716-446655440001/segments" \
  -F "segment_data={\"object_id\":\"demo-video\",\"timerange\":\"2025-08-23T19:00:00Z/2025-08-23T19:05:00Z\"}"

# Step 5: Verify final object state
curl -X GET "http://localhost:8000/objects/demo-video" | jq .
```

**Expected Result**: The object will have 3 flow references, showing how the same media content is referenced across different time periods.

### Media Content Access Workflow

```bash
# 1. Get segment information
SEGMENT_INFO=$(curl -s "http://localhost:8000/flows/550e8400-e29b-41d4-a716-446655440001/segments" | jq '.[0]')

# 2. Extract URLs
GET_URL=$(echo $SEGMENT_INFO | jq -r '.get_urls[] | select(.label | contains("GET")) | .url')
HEAD_URL=$(echo $SEGMENT_INFO | jq -r '.get_urls[] | select(.label | contains("HEAD")) | .url')

# 3. Check metadata first
echo "Checking segment metadata..."
curl -I "$HEAD_URL"

# 4. Download content if needed
echo "Downloading segment content..."
curl -O "$GET_URL"

# 5. Verify download
echo "Download complete. File size:"
ls -lh $(basename "$GET_URL" | cut -d'?' -f1)
```

## 📊 Analytics and Monitoring

### Get Analytics

```bash
# Flow usage analytics
curl "http://localhost:8000/analytics/flow-usage"

# Storage usage analytics
curl "http://localhost:8000/analytics/storage-usage"

# Time range analysis
curl "http://localhost:8000/analytics/time-range-analysis"
```

### Webhook Management

```bash
# Create webhook for event notifications
curl -X POST "http://localhost:8000/service/webhooks" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://webhook.example.com/events",
    "api_key_name": "X-API-Key",
    "api_key_value": "your-webhook-secret",
    "events": ["flows/segments_added"],
    "owner_id": "user123",
    "created_by": "user123"
  }'

# List registered webhooks
curl "http://localhost:8000/service/webhooks"
```

## ⚠️ Error Handling

### Common Error Scenarios

#### **Segment Creation Errors**

```bash
# Missing required fields
curl -X POST "http://localhost:8000/flows/550e8400-e29b-41d4-a716-446655440001/segments" \
  -F "segment_data={\"object_id\":\"seg_001\"}"
# Response: 422 Unprocessable Entity - timerange is required

# Invalid timerange format
curl -X POST "http://localhost:8000/flows/550e8400-e29b-41d4-a716-446655440001/segments" \
  -F "segment_data={\"object_id\":\"seg_001\",\"timerange\":\"invalid-format\"}"
# Response: 422 Unprocessable Entity - Invalid time range format

# Flow not found
curl -X POST "http://localhost:8000/flows/non-existent-flow/segments" \
  -F "segment_data={\"object_id\":\"seg_001\",\"timerange\":\"2025-08-23T14:00:00Z/2025-08-23T14:05:00Z\"}"
# Response: 404 Not Found - Flow not found
```

#### **URL Access Errors**

```bash
# Expired pre-signed URL
curl "http://s3.example.com/expired-url"
# Response: 403 Forbidden - URL expired

# Object not found in S3
curl "http://s3.example.com/non-existent-object"
# Response: 404 Not Found - Object doesn't exist

# Permission denied
curl "http://s3.example.com/restricted-object"
# Response: 403 Forbidden - Access denied
```

### Error Response Format

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

## 💡 Best Practices

### URL Management

1. **Always check metadata first**: Use HEAD URLs to verify file existence and size before downloading
2. **Handle URL expiration**: Pre-signed URLs expire; refresh them when needed
3. **Use appropriate URL type**: GET for content, HEAD for metadata
4. **Cache URLs efficiently**: Don't regenerate URLs unnecessarily

### Segment Creation

1. **Use consistent object IDs**: Reuse object IDs across multiple timeranges for efficiency
2. **Validate timerange format**: Always use ISO 8601 format
3. **Use multipart form**: Most reliable method for segment creation
4. **Handle large files**: Consider chunked uploads for very large media files

### Object Management

1. **Let objects auto-create**: Don't pre-create objects unless necessary
2. **Monitor flow references**: Check object details to see all referencing segments
3. **Use soft delete**: Preserve data with soft delete for safety
4. **Clean up unused objects**: Remove objects that are no longer referenced

### Performance Optimization

1. **Batch operations**: Create multiple segments in sequence
2. **Efficient queries**: Use timerange filtering for large datasets
3. **URL caching**: Cache pre-signed URLs to reduce API calls
4. **Parallel downloads**: Use multiple URLs for large content

### Security Considerations

1. **Validate inputs**: Always validate timerange and object_id formats
2. **Handle errors gracefully**: Don't expose internal errors to clients
3. **Monitor access patterns**: Track URL usage for security analysis
4. **Rotate credentials**: Regularly update S3 and database credentials

## 🔧 Troubleshooting

### Common Issues and Solutions

#### **Segment Upload Issues**

If segment creation fails:

1. **Check Required Fields**: Ensure `object_id` and `timerange` are provided
2. **Timerange Format**: Use ISO 8601 format (e.g., "2025-08-23T14:00:00Z/2025-08-23T14:05:00Z")
3. **Use Working Methods**: 
   - ✅ **Multipart Form**: Use `segment_data` field + `file` field for media content
   - ✅ **Form Only**: Use `segment_data` field for metadata without media file
   - ⚠️ **JSON Only**: Currently not working due to FastAPI parameter binding issue
4. **File Upload**: Ensure file is properly attached when using multipart form
5. **JSON Validation**: Check that all required fields match the FlowSegment model
6. **Flow ID**: Verify the flow ID exists and is not read-only

#### **Object Management Issues**

If object operations fail:

1. **Object ID Consistency**: Use the same `object_id` across multiple segments to reuse objects
2. **Automatic Creation**: Objects are created automatically when first referenced in segments
3. **Flow References**: Each segment adds a new flow reference to the object
4. **Timerange Uniqueness**: Use different timeranges for segments with the same object ID
5. **Object Lookup**: Use `/objects/{object_id}` endpoint to check object details and flow references

#### **URL Access Issues**

If URL access fails:

1. **Check URL Expiration**: Pre-signed URLs expire after 1 hour by default
2. **Verify Object Existence**: Ensure the S3 object actually exists
3. **Check Permissions**: Verify S3 bucket permissions and access keys
4. **Network Connectivity**: Ensure network access to S3 endpoint
5. **URL Format**: Verify the URL is properly formatted and not corrupted

### Debugging Tips

1. **Enable Debug Logging**: Set `LOG_LEVEL=DEBUG` in environment
2. **Check API Responses**: Use `jq` to format JSON responses for readability
3. **Verify S3 State**: Check S3 bucket contents directly
4. **Monitor Database**: Check VAST database tables for data consistency
5. **Test URLs**: Test pre-signed URLs directly with curl

## 📚 Additional Resources

- **[API Reference](API_REFERENCE.md)** - Complete API endpoint documentation
- **[Architecture Guide](ARCHITECTURE.md)** - Technical architecture details
- **[Deployment Guide](DEPLOYMENT.md)** - Deployment and configuration
- **[Observability Guide](OBSERVABILITY.md)** - Monitoring and observability setup
- **[Soft Delete Extension](SOFT_DELETE_EXTENSION.md)** - Soft delete functionality
- **[Interactive API Docs](http://localhost:8000/docs)** - Swagger UI documentation
- **[ReDoc Documentation](http://localhost:8000/redoc)** - Alternative API documentation
