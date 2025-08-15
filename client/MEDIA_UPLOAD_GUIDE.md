# Media Upload Guide for TAMS API

This guide explains how to upload media files to the TAMS (Time-addressable Media Store) API, covering both single media uploads and series of media files.

## Table of Contents
- [Single Media Upload](#single-media-upload)
- [Series of Media Upload](#series-of-media-upload)
- [Media Upload Workflow](#media-upload-workflow)
- [API Endpoints Used](#api-endpoints-used)
- [Error Handling](#error-handling)
- [Examples](#examples)

## Single Media Upload

### Overview
A single media upload involves creating a source, flow, allocating storage, uploading the media file, and creating a flow segment.

### Steps
1. **Create Source** - Define the media source (e.g., camera, file, stream)
2. **Create Flow** - Create a media flow with metadata
3. **Allocate Storage** - Get presigned URLs for S3 upload
4. **Upload Media** - Upload media file to S3 using presigned URL
5. **Create Segment** - Create flow segment linking media to flow

### Example Using CLI Tool
```bash
# Upload a single media
python tams_video_upload.py video_file.mp4

# With custom metadata
python tams_video_upload.py video_file.mp4 \
  --source-name "Security Camera 1" \
  --flow-name "Daily Recording" \
  --resolution "1920x1080" \
  --frame-rate "30/1" \
  --codec "video/mp4"
```

## Series of Media Upload

### Overview
A series of media represents multiple related media files that should be organized together (e.g., episodes, daily recordings, multi-camera views).

### Approaches

#### Method 1: Sequential Upload with Common Source
```bash
# Create a common source for all media
python tams_video_upload.py episode_01.mp4 \
  --source-name "TV Series Season 1" \
  --flow-name "Episode 01" \
  --series-mode

python tams_video_upload.py episode_02.mp4 \
  --source-name "TV Series Season 1" \
  --flow-name "Episode 02" \
  --series-mode

python tams_video_upload.py episode_03.mp4 \
  --source-name "TV Series Season 1" \
  --flow-name "Episode 03" \
  --series-mode
```

#### Method 2: Batch Upload Script
```python
#!/usr/bin/env python3
"""
Batch video upload script for series of videos
"""

import os
import sys
from pathlib import Path
from tams_video_uploader import TAMSVideoUploader

def upload_series(base_source_name: str, video_directory: str, flow_prefix: str = "Episode"):
    """Upload a series of videos from a directory"""
    
    uploader = TAMSVideoUploader()
    video_files = list(Path(video_directory).glob("*.mp4"))
    video_files.sort()  # Ensure consistent ordering
    
    print(f"🎬 Uploading series: {base_source_name}")
    print(f"📁 Found {len(video_files)} video files")
    
    for i, video_file in enumerate(video_files, 1):
        print(f"\n📤 Uploading {video_file.name} ({i}/{len(video_files)})")
        
        try:
            # Upload with series naming
            flow_name = f"{flow_prefix} {i:02d}"
            
            success = uploader.upload_video(
                video_path=video_file,
                source_name=base_source_name,
                flow_name=flow_name,
                resolution="1920x1080",
                frame_rate="30/1",
                codec="video/mp4"
            )
            
            if success:
                print(f"✅ Successfully uploaded {video_file.name}")
            else:
                print(f"❌ Failed to upload {video_file.name}")
                
        except Exception as e:
            print(f"❌ Error uploading {video_file.name}: {e}")
    
    print(f"\n🎉 Series upload complete: {base_source_name}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python batch_upload.py <source_name> <video_directory>")
        print("Example: python batch_upload.py 'TV Series Season 1' ./episodes/")
        sys.exit(1)
    
    source_name = sys.argv[1]
    video_dir = sys.argv[2]
    
    if not os.path.isdir(video_dir):
        print(f"Error: {video_dir} is not a valid directory")
        sys.exit(1)
    
    upload_series(source_name, video_dir)
```

## Media Upload Workflow

### 1. Source Creation
- **Purpose**: Identifies the origin of media content
- **Examples**: Camera ID, file path, stream URL, device name
- **Metadata**: Name, description, location, type

### 2. Flow Creation
- **Purpose**: Organizes related media content
- **Examples**: Episode, recording session, event, time period
- **Metadata**: Name, description, tags, content format, time range

### 3. Storage Allocation
- **Purpose**: Reserves S3 storage space and generates upload URLs
- **Process**: Creates presigned URLs for secure, direct S3 uploads
- **Timeout**: Configurable (default: 1 hour)

### 4. Media Upload
- **Method**: Direct S3 upload using presigned URL
- **Headers**: Minimal headers to avoid signature validation issues
- **Fallback**: Automatic retry with different HTTP libraries

### 5. Segment Creation
- **Purpose**: Links uploaded media to flow with timing information
- **Metadata**: Object ID, timerange, sample offsets, key frame count

## API Endpoints Used

### POST /sources
Creates a new media source
```json
{
  "name": "Security Camera 1",
  "description": "Main entrance camera",
  "type": "camera",
  "location": "Main Entrance"
}
```

### POST /flows
Creates a new media flow
```json
{
  "name": "Daily Recording",
  "description": "24-hour security recording",
  "type": "VideoFlow",
  "tags": {"category": "security", "location": "entrance"},
  "content_format": {
    "mime_type": "video/mp4",
    "codec": "video/mp4",
    "frame_width": 1920,
    "frame_height": 1080,
    "frame_rate": "30/1"
  }
}
```

### POST /flows/{flow_id}/storage
Allocates storage for media objects
```json
{
  "limit": 1
}
```

### POST /flows/{flow_id}/segments
Creates flow segment linking media to flow
```json
{
  "object_id": "uuid-of-uploaded-video",
  "timerange": "[00:00:00.000,00:05:00.000)",
  "ts_offset": "0:0",
  "sample_offset": 0,
  "sample_count": 0,
  "key_frame_count": 0
}
```

## ⚠️ S3 Upload Best Practices

### Presigned URL Headers
When uploading to S3 using presigned URLs, **never add custom headers** unless they were included in the original signature generation. Adding headers like:
- `Content-Type`
- `x-amz-acl`
- `x-amz-metadata-*`
- `Content-MD5`

Will cause `SignatureDoesNotMatch` errors and upload failures.

### HTTP Library Compatibility
- **urllib PUT requests**: Not recommended for S3 uploads due to header handling limitations
- **requests library**: Better compatibility with S3 presigned URLs
- **boto3**: Best compatibility but requires AWS credentials

The provided uploader scripts automatically handle these compatibility issues and use the most appropriate HTTP method for each situation.

### Why Headers Matter
S3 presigned URLs are cryptographically signed with specific parameters. When you add headers that weren't part of the original signature:
1. S3 receives the request with unexpected headers
2. S3 recalculates the signature including your headers
3. The signatures don't match → `403 SignatureDoesNotMatch`
4. Upload fails

## Error Handling

### Common Issues and Solutions

#### S3 Upload Failures
- **403 Forbidden**: Check S3 credentials and bucket permissions
- **SignatureDoesNotMatch**: Don't add custom headers to presigned URLs
- **Connection Timeout**: Increase timeout values in client

#### Common S3 Upload Mistakes
1. **Adding Content-Type header**: Let S3 infer the type from the file extension
2. **Adding x-amz-acl header**: Use bucket default permissions instead
3. **Using urllib PUT directly**: Use the provided uploader scripts
4. **Adding Content-MD5**: Can cause signature mismatches with presigned URLs

#### S3 Upload Best Practices
1. **Use minimal headers**: Only send what's absolutely necessary
2. **Let S3 infer metadata**: Don't override content type or other properties
3. **Use compatible HTTP libraries**: The uploader scripts handle this automatically
4. **Test with small files first**: Verify the upload process works before large files

#### API Errors
- **400 Bad Request**: Validate request payload format
- **404 Not Found**: Ensure flow/source IDs exist
- **500 Internal Server Error**: Check server logs for details

#### File Issues
- **File Not Found**: Verify file path and permissions
- **Unsupported Format**: Use MP4, MOV, or other supported formats
- **File Too Large**: Check S3 upload limits

## Examples

### Example 1: Security Camera Recording
```bash
# Upload daily security recording
python tams_video_upload.py security_recording_2024_01_15.mp4 \
  --source-name "Main Entrance Camera" \
  --flow-name "Daily Recording 2024-01-15" \
  --resolution "1920x1080" \
  --frame-rate "30/1"
```

### Example 2: TV Series Episodes
```bash
# Upload series episodes
python batch_media_upload.py "Breaking Bad Season 1" ./episodes/
```

### Example 3: Multi-Camera Event
```bash
# Upload multiple camera angles for an event
python tams_video_upload.py camera_1_event.mp4 \
  --source-name "Event Camera 1" \
  --flow-name "Annual Conference 2024"

python tams_video_upload.py camera_2_event.mp4 \
  --source-name "Event Camera 2" \
  --flow-name "Annual Conference 2024"
```

## Best Practices

1. **Consistent Naming**: Use consistent naming conventions for sources and flows
2. **Metadata**: Include relevant metadata for better organization
3. **Error Handling**: Implement proper error handling and retry logic
4. **Batch Operations**: Use batch scripts for large numbers of media files
5. **Monitoring**: Monitor upload progress and handle failures gracefully
6. **Cleanup**: Remove temporary files after successful uploads

## Troubleshooting

### Check Server Status
```bash
curl http://localhost:8000/health
```

### Verify S3 Connection
```bash
python -c "
from app.storage.s3_store import S3Store
store = S3Store()
print('S3 connection:', store.s3_client.list_buckets())
"
```

### Test API Endpoints
```bash
# Test source creation
curl -X POST http://localhost:8000/sources \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Source", "type": "test"}'

# Test flow creation
curl -X POST http://localhost:8000/flows \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Flow", "type": "VideoFlow"}'
```

## Support

For issues and questions:
- Check server logs for detailed error information
- Verify configuration settings in `config.py`
- Test individual API endpoints for connectivity
- Review S3 bucket permissions and credentials
