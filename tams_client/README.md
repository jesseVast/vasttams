# TAMS Python Client

Python client library for TAMS (Time-addressable Media Store) API.

## Installation

```bash
pip install -e .
```

## Features

- **Object-Oriented API**: Fluent, intuitive interface with domain objects
- **Automatic Token Management**: Handles authentication and token renewal automatically
- **Async/Sync Support**: All operations available in both async and sync forms
- **Auto-Probe**: Automatically extracts media parameters from first segment using ffprobe
- **Type Safety**: Pydantic models for request/response validation

## Quick Start

### Async Usage

```python
import asyncio
from tams_client import TAMSClient

async def main():
    # Create client
    async with TAMSClient("http://localhost:8000", "username", "password") as client:
        # Create a source
        source = client.TAMSSource(
            format="urn:x-nmos:format:video",
            label="My Video Source"
        )
        await source._ensure_created()  # Create on server
        
        # Create a flow (minimal data)
        flow = source.TAMSFlow(
            format="urn:x-nmos:format:video",
            codec="video/h264",
            label="My Video Flow"
        )
        await flow._ensure_created()  # Create on server
        
        # Add a segment (auto-probes file and updates flow)
        segment = await flow.add_segment(
            file_path="/path/to/video.mp4",
            timerange={"value": "[0:0_10:0)"}
        )
        
        print(f"Created segment: {segment.object_id}")

asyncio.run(main())
```

### Sync Usage

```python
from tams_client import TAMSClient

# Create client
client = TAMSClient("http://localhost:8000", "username", "password")

# Create a source
source = client.TAMSSource(
    format="urn:x-nmos:format:video",
    label="My Video Source"
)
asyncio.run(source._ensure_created())

# Create a flow
flow = source.TAMSFlow(
    format="urn:x-nmos:format:video",
    codec="video/h264",
    label="My Video Flow"
)
asyncio.run(flow._ensure_created())

# Add a segment
segment = asyncio.run(flow.add_segment(
    file_path="/path/to/video.mp4",
    timerange={"value": "[0:0_10:0)"}
))

print(f"Created segment: {segment.object_id}")

# Clean up
asyncio.run(client.close())
```

## API Reference

### TAMSClient

Main client class for interacting with TAMS servers.

#### Methods

- `TAMSSource(format, label=None, **kwargs)` - Create a new source
- `TAMSFlow(source_id, format, codec, label=None, **kwargs)` - Create a new flow
- `get_source(source_id)` - Get a source by ID
- `get_flow(flow_id)` - Get a flow by ID
- `list_sources(**query_params)` - List sources
- `list_flows(**query_params)` - List flows

### TAMSSource

Source domain object.

#### Methods

- `TAMSFlow(format, codec, label=None, **kwargs)` - Create a new flow for this source
- `add_flow(flow)` - Add a flow to this source
- `get_flow(flow_id)` - Get a flow by ID
- `list_flows(**query_params)` - List flows for this source
- `update(**updates)` - Update source metadata
- `delete()` - Delete source
- `get_tags()` - Get all tags
- `set_tag(name, value)` - Set or update a tag
- `delete_tag(name)` - Delete a tag

### TAMSFlow

Flow domain object.

#### Methods

- `add_segment(file_path=None, s3_object=None, timerange=None, auto_probe=True, **kwargs)` - Add a segment
  - If `auto_probe=True` and this is the first segment, automatically probes the file and updates flow essence parameters
  - Handles storage allocation, file upload, and segment creation in one call
- `get_segment(segment_id)` - Get a segment by object_id
- `list_segments(**query_params)` - List segments for this flow
- `delete_segments(**filters)` - Delete segments matching filters
- `update(**updates)` - Update flow metadata
- `delete()` - Delete flow
- `get_tags()` - Get all tags
- `set_tag(name, value)` - Set or update a tag
- `delete_tag(name)` - Delete a tag

### TAMSSegment

Segment domain object.

#### Methods

- `refresh()` - Refresh segment data from server
- `delete()` - Delete segment
- `update(**updates)` - Update segment metadata

## Examples

### Creating a Complete Workflow

```python
async def create_workflow():
    async with TAMSClient("http://localhost:8000", "user", "pass") as client:
        # Create source
        source = client.TAMSSource(
            format="urn:x-nmos:format:video",
            label="Camera Feed"
        )
        await source._ensure_created()
        
        # Create flow with minimal data
        flow = source.TAMSFlow(
            format="urn:x-nmos:format:video",
            codec="video/h264",
            label="HD Stream"
        )
        await flow._ensure_created()
        
        # Add segments (first one auto-probes)
        for i in range(3):
            segment = await flow.add_segment(
                file_path=f"/path/to/segment_{i}.mp4",
                timerange={"value": f"[{i*10}:0_{(i+1)*10}:0)"}
            )
            print(f"Added segment {i}: {segment.object_id}")
```

### Working with Tags

```python
async def tag_example():
    async with TAMSClient("http://localhost:8000", "user", "pass") as client:
        source = await client.get_source("source-id")
        
        # Set tags
        await source.set_tag("location", "studio-a")
        await source.set_tag("camera", "panasonic")
        
        # Get tags
        tags = await source.get_tags()
        print(tags)  # {"location": "studio-a", "camera": "panasonic"}
        
        # Get specific tag
        location = await source.get_tag("location")
        print(location)  # "studio-a"
        
        # Delete tag
        await source.delete_tag("camera")
```

## Requirements

- Python 3.10+
- aiohttp >= 3.9.0
- pydantic >= 2.0.0
- ffprobe (for auto-probe feature)

## License

MIT

