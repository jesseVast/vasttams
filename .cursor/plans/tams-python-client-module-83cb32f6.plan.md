<!-- 83cb32f6-c83d-40bd-a70a-f4de2253769c aa24de0d-4d19-42ac-95c1-ca08a8e167ac -->
# TAMS Python Client Module Implementation Plan

## Overview

Create a new independently installable Python module in `tams_client/src/` that provides a clean, modern interface for Python developers to interact with TAMS servers.

## Directory Structure

```
tams_client/
├── src/
│   └── tams_client/
│       ├── __init__.py
│       ├── client.py            # Main TAMSClient class with auth & token management
│       ├── auth.py               # Authentication and token renewal logic
│       ├── models.py             # Pydantic models for requests/responses
│       ├── domain/
│       │   ├── __init__.py
│       │   ├── source.py         # TAMSSource class - encapsulates source operations
│       │   ├── flow.py           # TAMSFlow class - encapsulates flow operations
│       │   ├── segment.py        # TAMSSegment class - encapsulates segment operations
│       │   └── base.py            # Base class for domain objects
│       ├── api/                  # Low-level API methods (hidden from users)
│       │   ├── __init__.py
│       │   ├── sources.py        # Source API calls
│       │   ├── flows.py          # Flow API calls
│       │   ├── segments.py       # Segment API calls
│       │   ├── objects.py        # Object API calls
│       │   ├── storage_backends.py # Storage backend API calls
│       │   └── tags.py           # Tags API calls
│       └── exceptions.py         # Custom exceptions
├── tests/
│   ├── __init__.py
│   ├── test_client.py
│   ├── test_auth.py
│   ├── test_domain.py            # Tests for domain objects
│   └── test_api.py               # Tests for low-level API
├── pyproject.toml                # Package configuration
├── setup.py                      # Setup script (optional, for compatibility)
├── README.md                     # Usage documentation
└── requirements.txt              # Dependencies
```

## Implementation Details

### 1. Package Configuration (`pyproject.toml`)

- Package name: `tams-client`
- Python requirement: `>=3.10`
- Dependencies:
  - `aiohttp>=3.9.0` (async HTTP)
  - `pydantic>=2.0.0` (data validation)
  - `typing-extensions>=4.0.0` (for Python 3.10 compatibility)

### 2. Authentication Module (`auth.py`)

- `TokenManager` class:
  - Stores username/password and server URL
  - Implements `login()` to get initial token via `/auth/login`
  - Implements `refresh_token()` for automatic renewal
  - Detects 401 responses and auto-refreshes tokens
  - Thread-safe token storage for sync operations
  - Async-safe token storage for async operations

### 3. Main Client Class (`client.py`)

- `TAMSClient` class with:
  - `__init__(server_url, username, password, timeout=30, verify_ssl=True)`
  - Async context manager support (`async with`)
  - Automatic token injection in request headers
  - Retry logic with token refresh on 401
  - Session management (reuse aiohttp.ClientSession)
  - Factory methods: `TAMSSource(...)`, `TAMSFlow(...)`, etc. (for creating new objects)
  - Query methods: `get_source(id)`, `get_flow(id)`, `list_sources()`, `list_flows()`, etc. (for retrieving existing objects)

### 4. Domain Objects (Object-Oriented API)

**`domain/base.py`**:

- `c`
  - Stores `client` reference and `id`
  - Provides async/sync method wrappers
  - Common operations (refresh, delete, update)

**`domain/source.py`**:

- `TAMSSource` class:
  - `__init__(client, **source_data)` - creates source via API
  - `add_flow(flow)` - adds a TAMSFlow object to this source (creates flow via API)
    - Accepts: `flow = TAMSFlow(source=self, format="...", codec="...", label="...")` (minimal data)
    - Returns: `TAMSFlow` instance (now created on server)
  - `get_flow(flow_id)` - retrieves existing flow
  - `list_flows(**query_params)` - lists flows for this source
  - `update(**updates)` - updates source metadata
  - `delete()` - deletes source
  - `get_tags()` - gets all tags
  - `set_tag(name, value)` - sets/updates a tag
  - `delete_tag(name)` - deletes a tag
  - Properties: `id`, `format`, `label`, `description`, etc.

**`domain/flow.py`**:

- `TAMSFlow` class:
  - `__init__(source, format, codec, label=None, **flow_data)` - creates flow with minimal data
    - Can be called before adding to source: `flow = TAMSFlow(source=source_obj, format="urn:x-nmos:format:video", codec="video/h264", label="My Flow")`
    - Or standalone: `TAMSFlow(client, source_id, format="...", codec="...", label="...")`
  - `add_segment(file_path=None, s3_object=None, timerange=None, auto_probe=True, **segment_data)` - combined operation:
    - If `auto_probe=True` and this is the first segment:
      - Probes file with ffmpeg (via `utils/ffmpeg_probe.py`)
      - Extracts essence parameters (resolution, frame_rate, bitrate, etc.)
      - Auto-updates flow with complete essence_parameters via `update()`
    - Allocates storage (gets presigned URL)
    - Uploads file or uses S3 object
    - Creates segment
    - Returns `TAMSSegment` object
  - `get_segment(segment_id)` - retrieves existing segment
  - `list_segments(**query_params)` - lists segments for this flow
  - `delete_segments(**filters)` - deletes segments matching filters
  - `update(**updates)` - updates flow metadata (used internally by add_segment for auto-probe)
  - `delete()` - deletes flow
  - `get_tags()` - gets all tags
  - `set_tag(name, value)` - sets/updates a tag
  - `delete_tag(name)` - deletes a tag
  - Properties: `id`, `source_id`, `format`, `codec`, `essence_parameters`, etc.
  - Internal: `_segment_count` - tracks number of segments added (for auto-probe detection)

**`domain/segment.py`**:

- `TAMSSegment` class:
  - `__init__(client, flow_id, segment_data)` - represents existing segment
  - `update(**updates)` - updates segment metadata
  - `delete()` - deletes segment
  - Properties: `object_id`, `timerange`, `flow_id`, etc.

### 5. Low-Level API Client (`api/` directory - internal use only)

These are used by domain objects, not exposed to users:

**`api/sources.py`**:

- `create_source(client, source_data) -> dict`
- `get_source(client, source_id) -> dict`
- `update_source(client, source_id, source_data) -> dict`
- `delete_source(client, source_id) -> None`
- `list_sources(client, query_params) -> List[dict]`

**`api/flows.py`**:

- `create_flow(client, flow_data) -> dict`
- `get_flow(client, flow_id) -> dict`
- `update_flow(client, flow_id, flow_data) -> dict`
- `delete_flow(client, flow_id) -> None`
- `list_flows(client, query_params) -> List[dict]`

**`api/segments.py`**:

- `create_segment(client, flow_id, segment_data, file_path=None) -> dict`
- `list_segments(client, flow_id, query_params) -> List[dict]`
- `delete_segments(client, flow_id, query_params) -> None`
- `allocate_storage(client, flow_id, label, limit, storage_id) -> dict`
- `upload_to_storage(client, presigned_url, data, content_type) -> bool`

**`api/objects.py`**:

- `get_object(client, object_id) -> dict`
- `list_objects(client, query_params) -> List[dict]`

**`api/storage_backends.py`**:

- `list_storage_backends(client) -> List[dict]`
- `get_storage_backend(client, backend_id) -> dict`
- `create_storage_backend(client, backend_data) -> dict`
- `update_storage_backend(client, backend_id, backend_data) -> dict`
- `delete_storage_backend(client, backend_id) -> None`

**`api/tags.py`**:

- `get_tags(client, entity_type, entity_id) -> dict`
- `get_tag(client, entity_type, entity_id, tag_name) -> str`
- `set_tag(client, entity_type, entity_id, tag_name, tag_value) -> None`
- `delete_tag(client, entity_type, entity_id, tag_name) -> None`

### 5. Models (`models.py`)

- Pydantic models for type safety:
  - Request models (SourcePost, FlowPost, SegmentPost, etc.)
  - Response models (Source, Flow, Segment, Object, StorageBackend)
  - Reuse existing models from `client/tams_ingestclient/models.py` where appropriate

### 6. Exceptions (`exceptions.py`)

- `TAMSClientError` (base exception)
- `TAMSAuthenticationError`
- `TAMSAPIError` (with status code and response body)
- `TAMSConnectionError`

### 7. Sync Wrapper Pattern

For each async method, provide a sync version:

```python
def create_flow_sync(self, flow_data: dict) -> dict:
    """Synchronous wrapper for create_flow"""
    return asyncio.run(self.create_flow(flow_data))
```

### 8. File Upload Implementation

- Use `aiohttp.FormData` for multipart uploads
- Support both file paths and file-like objects
- Handle large files with streaming
- Progress callback support (optional)

## Key Features

1. **Automatic Token Renewal**: Intercepts 401 responses and automatically refreshes tokens
2. **Async/Sync Support**: All methods available in both async and sync forms
3. **Type Safety**: Pydantic models for request/response validation
4. **Error Handling**: Comprehensive exception hierarchy
5. **Session Reuse**: Efficient connection pooling with aiohttp
6. **Python 3.10+**: Uses modern Python features (type hints, async context managers)
7. **Tags Management**: Full CRUD operations for tags on sources, flows, and segments with search capabilities
8. **Combined Operations**: `create_object_and_segment()` method handles full workflow (allocate → upload → create segment) with support for local files or S3 objects
9. **Fluent Builder Pattern**: Operation classes enable chainable workflows for complex multi-step operations

## Testing Strategy

- Unit tests for authentication and token renewal
- Integration tests for each endpoint (can use test fixtures from existing test suite)
- Mock aiohttp responses for isolated testing

## Documentation

- README.md with usage examples for both async and sync patterns
- API documentation in docstrings
- Example scripts showing common workflows