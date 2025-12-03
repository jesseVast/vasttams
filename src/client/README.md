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

# Use sync wrapper methods
source = client.get_source_sync("source-id")
flow = client.get_flow_sync("flow-id")
sources = client.list_sources_sync()
flows = client.list_flows_sync()

# Note: For creating sources/flows/segments, you still need to use async methods
# or wrap them with asyncio.run() as domain objects don't have sync wrappers
```

## API Reference

### TAMSClient

Main client class for interacting with TAMS servers.

#### Methods

**Source and Flow Operations:**
- `TAMSSource(format, label=None, **kwargs)` - Create a new source
- `TAMSFlow(source_id, format, codec, label=None, **kwargs)` - Create a new flow
- `get_source(source_id)` - Get a source by ID (async)
- `get_flow(flow_id)` - Get a flow by ID (async)
- `list_sources(**query_params)` - List sources (async)
- `list_flows(**query_params)` - List flows (async)

**Synchronous Wrappers:**
- `get_source_sync(source_id)` - Get a source by ID (sync)
- `get_flow_sync(flow_id)` - Get a flow by ID (sync)
- `list_sources_sync(**query_params)` - List sources (sync)
- `list_flows_sync(**query_params)` - List flows (sync)

**Vector Operations (VAST Extensions):**
- `search_vectors(vector, limit=10, distance_metric="L2", distance_threshold=None)` - Search for objects by vector similarity (async)
- `update_object_vector(object_id, vector, summary=None, embedding_model=None)` - Update or set vector for an object (async)
- `get_object_vector(object_id)` - Get vector data for an object (async)
- `delete_object_vector(object_id)` - Delete vector data for an object (async)

**Synchronous Vector Wrappers:**
- `search_vectors_sync(vector, limit=10, distance_metric="L2", distance_threshold=None)` - Search for objects by vector similarity (sync)
- `update_object_vector_sync(object_id, vector, summary=None, embedding_model=None)` - Update or set vector for an object (sync)
- `get_object_vector_sync(object_id)` - Get vector data for an object (sync)
- `delete_object_vector_sync(object_id)` - Delete vector data for an object (sync)

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

### Working with Vector Operations

#### Async Vector Operations

```python
async def vector_example():
    async with TAMSClient("http://localhost:8000", "user", "pass") as client:
        object_id = "obj-123"
        
        # Update object vector
        result = await client.update_object_vector(
            object_id=object_id,
            vector=[0.1, 0.2, 0.3, 0.4, 0.5],
            summary="Example video segment",
            embedding_model="clip-vit-base-patch32"
        )
        print(f"Updated vector: {result}")
        
        # Get object vector
        vector_data = await client.get_object_vector(object_id)
        if vector_data:
            print(f"Vector: {vector_data['vector']}")
            print(f"Summary: {vector_data.get('summary')}")
        
        # Search for similar objects
        query_vector = [0.1, 0.2, 0.3, 0.4, 0.5]
        results = await client.search_vectors(
            vector=query_vector,
            limit=10,
            distance_metric="L2",
            distance_threshold=0.5
        )
        print(f"Found {len(results)} similar objects")
        for result in results:
            print(f"  Object {result['object_id']}: distance={result['distance']}")
        
        # Delete vector
        deleted = await client.delete_object_vector(object_id)
        print(f"Vector deleted: {deleted}")
```

#### Sync Vector Operations

```python
from tams_client import TAMSClient

client = TAMSClient("http://localhost:8000", "user", "pass")

object_id = "obj-123"

# Update object vector (synchronous)
result = client.update_object_vector_sync(
    object_id=object_id,
    vector=[0.1, 0.2, 0.3, 0.4, 0.5],
    summary="Example video segment",
    embedding_model="clip-vit-base-patch32"
)
print(f"Updated vector: {result}")

# Get object vector (synchronous)
vector_data = client.get_object_vector_sync(object_id)
if vector_data:
    print(f"Vector: {vector_data['vector']}")
    print(f"Summary: {vector_data.get('summary')}")

# Search for similar objects (synchronous)
query_vector = [0.1, 0.2, 0.3, 0.4, 0.5]
results = client.search_vectors_sync(
    vector=query_vector,
    limit=10,
    distance_metric="L2",
    distance_threshold=0.5
)
print(f"Found {len(results)} similar objects")

# Delete vector (synchronous)
deleted = client.delete_object_vector_sync(object_id)
print(f"Vector deleted: {deleted}")
```

## Requirements

- Python 3.10+
- aiohttp >= 3.9.0
- pydantic >= 2.0.0
- requests >= 2.31.0
- typing-extensions >= 4.0.0
- ffprobe (for auto-probe feature)

## License

MIT

