# TAMS Ingest Client

A unified client for uploading all media types to TAMS (Time-addressable Media Store) service with automatic source/flow creation, media analysis, and S3 integration.

## Features

- **Multi-Media Support**: Supports video, audio, image, and data files
- **Automatic Source/Flow Creation**: Creates TAMS sources and flows automatically based on media analysis
- **Unified Media Analysis**: Uses FFmpeg to analyze all media types and auto-detect parameters
- **S3 Integration**: Uploads media segments to S3 with presigned URLs
- **Smart Segment Management**: Creates appropriate segments based on media type
- **Flexible Configuration**: Supports TOML files, environment variables, and programmatic configuration
- **Error Handling**: Comprehensive error handling and retry logic
- **Async Support**: Full async/await support for high-performance operations

## Supported Media Types

The TAMS Ingest Client supports all TAMS-compatible media formats:

### Video Files
- **Formats**: MP4, AVI, MOV, MKV, WebM, M4V, FLV, WMV
- **Codecs**: H.264, H.265, VP8, VP9, AV1
- **Analysis**: Resolution, frame rate, bitrate, duration, codec detection

### Audio Files  
- **Formats**: MP3, WAV, AAC, FLAC, OGG, M4A, WMA, Opus
- **Codecs**: AAC, MP3, Opus, Vorbis, FLAC, WMA, PCM
- **Analysis**: Sample rate, channels, bitrate, duration, codec detection

### Image Files
- **Formats**: JPEG, PNG, GIF, BMP, TIFF, WebP, SVG, ICO
- **Codecs**: JPEG, PNG, GIF, BMP, TIFF, WebP
- **Analysis**: Dimensions, color space, pixel format

### Data Files
- **Formats**: JSON, XML, CSV, TXT, LOG, DAT, BIN
- **Analysis**: File size, encoding, line count (for text files)

## Quick Start

### Basic Usage

```python
from src.tams_ingestclient import UnifiedTAMSIngestClient, TAMSIngestConfig

# Load configuration
config = TAMSIngestConfig.from_toml("config.toml")

# Create client
client = UnifiedTAMSIngestClient(config)

# Ingest any media type
result = await client.ingest_media("path/to/media.mp4")  # Video
result = await client.ingest_media("path/to/audio.mp3")  # Audio  
result = await client.ingest_media("path/to/image.jpg")  # Image
result = await client.ingest_media("path/to/data.json")  # Data

print(f"Success: {result.success}")
print(f"Source ID: {result.source_id}")
print(f"Flow ID: {result.flow_id}")
print(f"Segments: {result.segment_count}")
```

### Advanced Usage

```python
from src.tams_ingestclient import (
    UnifiedTAMSIngestClient, 
    VideoIngestRequest, 
    TAMSSourceConfig, 
    TAMSFlowConfig,
    TAMSIngestConfig
)

# Create client with custom configuration
config = TAMSIngestConfig(
    tams_api=TAMSApiConfig(base_url="http://localhost:8000"),
    s3=S3Config(bucket="my-videos", prefix="ingested"),
    video_processing=VideoProcessingConfig(chunk_duration=60)
)

client = UnifiedTAMSIngestClient(config)

# Create custom source and flow configurations
source_config = TAMSSourceConfig(
    label="My Video Source",
    description="Custom video source",
    tags={"category": "demo", "quality": "high"}
)

flow_config = TAMSFlowConfig(
    source_id="source-id-here",
    label="My Video Flow",
    codec="h264",
    frame_width=1920,
    frame_height=1080
)

# Ingest video with custom configurations
request = VideoIngestRequest(
    video_path="path/to/video.mp4",
    source_config=source_config,
    flow_config=flow_config,
    chunk_duration=30,
    upload_to_s3=True
)

result = await client.ingest_video(request)
```

## Configuration

### TOML Configuration

```toml
[tams_ingest]

# Core settings
enable_logging = true
log_level = "INFO"
max_concurrent_uploads = 5
auto_create_source = true
auto_create_flow = true
upload_to_s3 = true

# TAMS API configuration
[tams_ingest.tams_api]
base_url = "http://localhost:8000"
api_key = "your-api-key"
timeout = 30
retry_attempts = 3
verify_ssl = false

# S3 configuration
[tams_ingest.s3]
bucket = "tams-videos"
prefix = "ingested"
region = "us-east-1"
endpoint_url = "http://localhost:9000"  # For MinIO
access_key = "minioadmin"
secret_key = "minioadmin"
use_ssl = false

# Video processing configuration
[tams_ingest.video_processing]
chunk_duration = 30
segment_overlap = 0
video_codec = "h264"
audio_codec = "aac"
auto_detect_codec = true
auto_detect_resolution = true
auto_detect_framerate = true
auto_detect_bitrate = true
```

### Environment Variables

```bash
export TAMS_BASE_URL="http://localhost:8000"
export TAMS_API_KEY="your-api-key"
export S3_BUCKET="tams-videos"
export S3_PREFIX="ingested"
export CHUNK_DURATION="30"
export LOG_LEVEL="INFO"
```

## API Reference

### Main Classes

#### `UnifiedTAMSIngestClient`

Main client class for TAMS video ingestion.

```python
client = UnifiedTAMSIngestClient(config)
result = await client.ingest_video(request)
```

#### `VideoIngestRequest`

Request model for video ingestion.

```python
request = VideoIngestRequest(
    video_path="path/to/video.mp4",
    chunk_duration=30,
    upload_to_s3=True,
    tags={"category": "demo"}
)
```

#### `TAMSSourceConfig`

Configuration for TAMS sources.

```python
source_config = TAMSSourceConfig(
    label="My Source",
    description="Video source",
    format="urn:x-nmos:format:video",
    tags={"type": "video"}
)
```

#### `TAMSFlowConfig`

Configuration for TAMS flows.

```python
flow_config = TAMSFlowConfig(
    source_id="source-id",
    label="My Flow",
    codec="h264",
    frame_width=1920,
    frame_height=1080
)
```

### Convenience Functions

#### `ingest_video_unified()`

```python
result = await ingest_video_unified(
    video_path="path/to/video.mp4",
    config=config
)
```

#### `create_source_unified()`

```python
source_id = await create_source_unified(
    source_config=source_config,
    config=config
)
```

#### `create_flow_unified()`

```python
flow_id = await create_flow_unified(
    flow_config=flow_config,
    config=config
)
```

## Video Analysis

The client automatically analyzes video files to extract:

- Duration, resolution, framerate
- Video and audio codecs
- Bitrates and file size
- Color space and pixel format
- Audio track presence

## S3 Integration

When S3 is configured, the client:

- Uploads video segments to S3
- Generates presigned URLs for access
- Manages S3 object keys and metadata
- Handles large file uploads with multipart upload

## Error Handling

The client provides comprehensive error handling:

- TAMS API errors with retry logic
- Video analysis failures
- S3 upload errors
- FFmpeg processing errors
- Configuration validation errors

## Dependencies

- `aiohttp` - Async HTTP client
- `pydantic` - Data validation
- `toml` - Configuration file parsing
- `ffmpeg` - Video processing (system dependency)
- `boto3` - S3 client (via store module)

## Examples

### Basic Video Ingestion

```python
import asyncio
from src.tams_ingestclient import ingest_video_unified, TAMSIngestConfig

async def main():
    config = TAMSIngestConfig.from_env()
    result = await ingest_video_unified("video.mp4", config)
    
    if result.success:
        print(f"Uploaded {result.segment_count} segments")
        print(f"Source: {result.source_id}")
        print(f"Flow: {result.flow_id}")
    else:
        print(f"Error: {result.error_message}")

asyncio.run(main())
```

### Custom Configuration

```python
from src.tams_ingestclient import (
    UnifiedTAMSIngestClient, 
    TAMSIngestConfig,
    TAMSApiConfig,
    S3Config,
    VideoProcessingConfig
)

config = TAMSIngestConfig(
    tams_api=TAMSApiConfig(
        base_url="http://tams.example.com",
        api_key="your-key"
    ),
    s3=S3Config(
        bucket="my-bucket",
        prefix="videos",
        endpoint_url="http://minio:9000"
    ),
    video_processing=VideoProcessingConfig(
        chunk_duration=60,
        video_codec="h265"
    )
)

client = UnifiedTAMSIngestClient(config)
```

### Batch Processing

```python
import asyncio
from pathlib import Path
from src.tams_ingestclient import ingest_video_unified, TAMSIngestConfig

async def process_videos(video_dir: str):
    config = TAMSIngestConfig.from_toml("config.toml")
    video_files = list(Path(video_dir).glob("*.mp4"))
    
    tasks = []
    for video_file in video_files:
        task = ingest_video_unified(str(video_file), config)
        tasks.append(task)
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            print(f"Error processing {video_files[i]}: {result}")
        else:
            print(f"Processed {video_files[i]}: {result.segment_count} segments")

asyncio.run(process_videos("videos/"))
```




