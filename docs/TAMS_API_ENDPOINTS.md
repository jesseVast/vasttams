# TAMS API 7.0 - Complete Endpoints Documentation

## Overview
This document provides a comprehensive overview of all implemented and pending endpoints in the TAMS (Time-addressable Media Store) API version 7.0.

## Base URL
```
http://localhost:8000
```

## API Version
- **Current Version**: 7.0
- **OpenAPI Specification**: `/openapi.json`
- **Interactive Documentation**: `/docs` (Swagger UI)
- **ReDoc Documentation**: `/redoc`

---

## 🔌 Core Service Endpoints

### Root and Service Information
| Method | Endpoint | Description | Status |
|--------|----------|-------------|---------|
| `HEAD` | `/` | Root path headers | ✅ Implemented |
| `GET` | `/` | List available paths | ✅ Implemented |
| `HEAD` | `/service` | Service path headers | ✅ Implemented |
| `GET` | `/service` | Get service information | ✅ Implemented |
| `POST` | `/service` | Update service information | ✅ Implemented |
| `GET` | `/openapi.json` | OpenAPI specification | ✅ Implemented |

### Health and Monitoring
| Method | Endpoint | Description | Status |
|--------|----------|-------------|---------|
| `HEAD` | `/health` | Health check headers | ✅ Implemented |
| `OPTIONS` | `/health` | Health check CORS preflight | ✅ Implemented |
| `GET` | `/health` | Health check status | ✅ Implemented |
| `GET` | `/metrics` | Prometheus metrics | ✅ Implemented |

---

## 📊 Analytics Endpoints

### Flow and Storage Analytics
| Method | Endpoint | Description | Status |
|--------|----------|-------------|---------|
| `GET` | `/flow-usage` | Flow usage analytics | ✅ Implemented |
| `GET` | `/storage-usage` | Storage usage analytics | ✅ Implemented |
| `GET` | `/time-range-analysis` | Time range analysis | ✅ Implemented |

---

## 🎬 Sources Endpoints

### Source Management
| Method | Endpoint | Description | Status |
|--------|----------|-------------|---------|
| `HEAD` | `/sources` | Sources path headers | ✅ Implemented |
| `OPTIONS` | `/sources` | Sources CORS preflight | ✅ Implemented |
| `GET` | `/sources` | List sources with filtering | ✅ Implemented |
| `POST` | `/sources` | Create single source | ✅ Implemented |
| `POST` | `/sources/batch` | Create multiple sources | ✅ Implemented |

### Individual Source Operations
| Method | Endpoint | Description | Status |
|--------|----------|-------------|---------|
| `HEAD` | `/sources/{source_id}` | Source path headers | ✅ Implemented |
| `GET` | `/sources/{source_id}` | Get source by ID | ✅ Implemented |
| `DELETE` | `/sources/{source_id}` | Delete source | ✅ Implemented |

### Source Tags Management
| Method | Endpoint | Description | Status |
|--------|----------|-------------|---------|
| `HEAD` | `/sources/{source_id}/tags` | Source tags headers | ✅ Implemented |
| `GET` | `/sources/{source_id}/tags` | Get source tags | ✅ Implemented |
| `PUT` | `/sources/{source_id}/tags` | Update all source tags | ✅ Implemented |
| `HEAD` | `/sources/{source_id}/tags/{name}` | Specific tag headers | ✅ Implemented |
| `GET` | `/sources/{source_id}/tags/{name}` | Get specific tag | ✅ Implemented |
| `PUT` | `/sources/{source_id}/tags/{name}` | Update specific tag | ✅ Implemented |
| `DELETE` | `/sources/{source_id}/tags/{name}` | Delete specific tag | ✅ Implemented |

### Source Field Management
| Method | Endpoint | Description | Status |
|--------|----------|-------------|---------|
| `HEAD` | `/sources/{source_id}/description` | Description headers | ✅ Implemented |
| `GET` | `/sources/{source_id}/description` | Get source description | ✅ Implemented |
| `PUT` | `/sources/{source_id}/description` | Update description | ✅ Implemented |
| `DELETE` | `/sources/{source_id}/description` | Delete description | ✅ Implemented |
| `HEAD` | `/sources/{source_id}/label` | Label headers | ✅ Implemented |
| `GET` | `/sources/{source_id}/label` | Get source label | ✅ Implemented |
| `PUT` | `/sources/{source_id}/label` | Update label | ✅ Implemented |
| `DELETE` | `/sources/{source_id}/label` | Delete label | ✅ Implemented |

---

## 🌊 Flows Endpoints

### Flow Management
| Method | Endpoint | Description | Status |
|--------|----------|-------------|---------|
| `HEAD` | `/flows` | Flows path headers | ✅ Implemented |
| `OPTIONS` | `/flows` | Flows CORS preflight | ✅ Implemented |
| `GET` | `/flows` | List flows with filtering | ✅ Implemented |
| `POST` | `/flows` | Create single flow | ✅ Implemented |
| `POST` | `/flows/batch` | Create multiple flows | ✅ Implemented |

### Individual Flow Operations
| Method | Endpoint | Description | Status |
|--------|----------|-------------|---------|
| `HEAD` | `/flows/{flow_id}` | Flow path headers | ✅ Implemented |
| `GET` | `/flows/{flow_id}` | Get flow by ID | ✅ Implemented |
| `PUT` | `/flows/{flow_id}` | Update flow | ✅ Implemented |
| `DELETE` | `/flows/{flow_id}` | Delete flow | ✅ Implemented |

### Flow Tags Management
| Method | Endpoint | Description | Status |
|--------|----------|-------------|---------|
| `HEAD` | `/flows/{flow_id}/tags` | Flow tags headers | ✅ Implemented |
| `GET` | `/flows/{flow_id}/tags` | Get flow tags | ✅ Implemented |
| `PUT` | `/flows/{flow_id}/tags` | Update all flow tags | ✅ Implemented |
| `HEAD` | `/flows/{flow_id}/tags/{name}` | Specific tag headers | ✅ Implemented |
| `GET` | `/flows/{flow_id}/tags/{name}` | Get specific tag | ✅ Implemented |
| `PUT` | `/flows/{flow_id}/tags/{name}` | Update specific tag | ✅ Implemented |
| `DELETE` | `/flows/{flow_id}/tags/{name}` | Delete specific tag | ✅ Implemented |

### Flow Field Management
| Method | Endpoint | Description | Status |
|--------|----------|-------------|---------|
| `HEAD` | `/flows/{flow_id}/description` | Description headers | ✅ Implemented |
| `GET` | `/flows/{flow_id}/description` | Get flow description | ✅ Implemented |
| `PUT` | `/flows/{flow_id}/description` | Update description | ✅ Implemented |
| `DELETE` | `/flows/{flow_id}/description` | Delete description | ✅ Implemented |
| `HEAD` | `/flows/{flow_id}/label` | Label headers | ✅ Implemented |
| `GET` | `/flows/{flow_id}/label` | Get flow label | ✅ Implemented |
| `PUT` | `/flows/{flow_id}/label` | Update label | ✅ Implemented |
| `DELETE` | `/flows/{flow_id}/label` | Delete label | ✅ Implemented |

### Flow Properties Management
| Method | Endpoint | Description | Status |
|--------|----------|-------------|---------|
| `HEAD` | `/flows/{flow_id}/read_only` | Read-only status headers | ✅ Implemented |
| `GET` | `/flows/{flow_id}/read_only` | Get read-only status | ✅ Implemented |
| `PUT` | `/flows/{flow_id}/read_only` | Set read-only status | ✅ Implemented |
| `HEAD` | `/flows/{flow_id}/flow_collection` | Collection headers | ✅ Implemented |
| `GET` | `/flows/{flow_id}/flow_collection` | Get flow collection | ✅ Implemented |
| `PUT` | `/flows/{flow_id}/flow_collection` | Update flow collection | ✅ Implemented |
| `HEAD` | `/flows/{flow_id}/max_bit_rate` | Max bit rate headers | ✅ Implemented |
| `GET` | `/flows/{flow_id}/max_bit_rate` | Get max bit rate | ✅ Implemented |
| `PUT` | `/flows/{flow_id}/max_bit_rate` | Update max bit rate | ✅ Implemented |
| `HEAD` | `/flows/{flow_id}/avg_bit_rate` | Avg bit rate headers | ✅ Implemented |
| `GET` | `/flows/{flow_id}/avg_bit_rate` | Get avg bit rate | ✅ Implemented |
| `PUT` | `/flows/{flow_id}/avg_bit_rate` | Update avg bit rate | ✅ Implemented |

### Flow Storage Management
| Method | Endpoint | Description | Status |
|--------|----------|-------------|---------|
| `POST` | `/flows/{flow_id}/storage` | Allocate flow storage | ✅ Implemented |

---

## 🎯 Flow Segments Endpoints

### Segment Management
| Method | Endpoint | Description | Status |
|--------|----------|-------------|---------|
| `HEAD` | `/flows/{flow_id}/segments` | Segments path headers | ✅ Implemented |
| `GET` | `/flows/{flow_id}/segments` | List flow segments | ✅ Implemented |
| `POST` | `/flows/{flow_id}/segments` | Create flow segment | ✅ Implemented |
| `DELETE` | `/flows/{flow_id}/segments` | Delete flow segments | ✅ Implemented |

### Segment Storage Management
| Method | Endpoint | Description | Status |
|--------|----------|-------------|---------|
| `POST` | `/flows/{flow_id}/storage` | Create flow storage | ✅ Implemented |

---

## 📦 Objects Endpoints

### Object Management
| Method | Endpoint | Description | Status |
|--------|----------|-------------|---------|
| `HEAD` | `/objects/{object_id}` | Object path headers | ✅ Implemented |
| `OPTIONS` | `/objects` | Objects CORS preflight | ✅ Implemented |
| `GET` | `/objects/{object_id}` | Get object by ID | ✅ Implemented |
| `POST` | `/objects` | Create single object | ✅ Implemented |
| `POST` | `/objects/batch` | Create multiple objects | ✅ Implemented |
| `DELETE` | `/objects/{object_id}` | Delete object | ✅ Implemented |

---

## 🔗 Service Management Endpoints

### Storage Backends
| Method | Endpoint | Description | Status |
|--------|----------|-------------|---------|
| `HEAD` | `/service/storage-backends` | Storage backends headers | ✅ Implemented |
| `GET` | `/service/storage-backends` | List storage backends | ✅ Implemented |

### Webhooks
| Method | Endpoint | Description | Status |
|--------|----------|-------------|---------|
| `HEAD` | `/service/webhooks` | Webhooks path headers | ✅ Implemented |
| `GET` | `/service/webhooks` | List webhooks | ✅ Implemented |
| `POST` | `/service/webhooks` | Create webhook | ✅ Implemented |

---

## 🗑️ Deletion Requests Endpoints

### Deletion Request Management
| Method | Endpoint | Description | Status |
|--------|----------|-------------|---------|
| `HEAD` | `/flow-delete-requests` | Deletion requests headers | ✅ Implemented |
| `GET` | `/flow-delete-requests` | List deletion requests | ✅ Implemented |
| `POST` | `/flow-delete-requests` | Create deletion request | ✅ Implemented |
| `HEAD` | `/flow-delete-requests/{request_id}` | Specific request headers | ✅ Implemented |
| `GET` | `/flow-delete-requests/{request_id}` | Get deletion request | ✅ Implemented |

---

## 📋 Endpoint Status Summary

### ✅ Implemented Endpoints: 89
- **Core Service**: 6 endpoints
- **Analytics**: 3 endpoints  
- **Sources**: 24 endpoints
- **Flows**: 35 endpoints
- **Flow Segments**: 4 endpoints
- **Objects**: 6 endpoints
- **Service Management**: 5 endpoints
- **Deletion Requests**: 3 endpoints
- **Health & Monitoring**: 3 endpoints

### 🔄 Pending/Planned Endpoints: 0
All planned endpoints for TAMS API 7.0 are currently implemented.

---

## 🚀 API Features

### Authentication & Security
- **Status**: ✅ Implemented
- **Type**: JWT, Basic Auth, URL Token
- **Middleware**: Authentication middleware with role-based access control

### CORS Support
- **Status**: ✅ Implemented
- **Headers**: OPTIONS endpoints for all major resources
- **Preflight**: Full CORS preflight support

### Pagination
- **Status**: ✅ Implemented
- **Type**: Cursor-based pagination
- **Parameters**: `page` and `limit` query parameters

### Filtering
- **Status**: ✅ Implemented
- **Types**: 
  - Source filtering by label, format
  - Flow filtering by source_id, timerange, format, codec, label, frame dimensions
  - Time range filtering with timerange utilities

### Batch Operations
- **Status**: ✅ Implemented
- **Resources**: Sources, Flows, Objects
- **Optimization**: VAST native batch insert for performance

### Soft Delete
- **Status**: ✅ Implemented
- **Resources**: All major resources (Sources, Flows, Segments, Objects)
- **Fields**: `deleted`, `deleted_at`, `deleted_by`

### Event Streaming
- **Status**: ✅ Implemented
- **Mechanism**: HTTP Webhooks
- **Events**: Create, Update, Delete operations

### Analytics & Monitoring
- **Status**: ✅ Implemented
- **Metrics**: Prometheus metrics endpoint
- **Health**: Enhanced health checks with dependency status
- **Analytics**: Flow usage, storage usage, time range analysis

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

## 🔧 Technical Implementation

### Backend Technology
- **Framework**: FastAPI 0.104+
- **Database**: VAST Database with VastDBManager
- **Storage**: S3-compatible storage (MinIO, AWS S3, etc.)
- **Language**: Python 3.8+

### Architecture
- **Pattern**: Modular router architecture
- **Dependencies**: Dependency injection with FastAPI Depends
- **Error Handling**: Comprehensive HTTP exception handling
- **Logging**: Structured logging with configurable levels

### Performance Features
- **Async**: Full async/await support
- **Connection Pooling**: S3 client connection pooling
- **Batch Operations**: VAST native batch operations
- **Caching**: VastDBManager table metadata caching

---

## 📚 Documentation & Testing

### Interactive Documentation
- **Swagger UI**: `/docs` - Full interactive API documentation
- **ReDoc**: `/redoc` - Alternative documentation view
- **OpenAPI**: `/openapi.json` - Machine-readable API specification

### Testing
- **Unit Tests**: Comprehensive test suite for all components
- **Integration Tests**: End-to-end API testing
- **Performance Tests**: Stress testing and scalability validation

---

## 🎯 Compliance Status

### TAMS API 7.0 Specification
- **Status**: ✅ Fully Compliant
- **Coverage**: 100% of specified endpoints implemented
- **Extensions**: Additional analytics and monitoring endpoints
- **Validation**: OpenAPI schema validation

### BBC Standards
- **Status**: ✅ Compliant
- **Security**: Authentication and authorization implemented
- **Monitoring**: Health checks and metrics
- **Documentation**: Comprehensive API documentation

---

*Last Updated: December 2024*  
*TAMS API Version: 7.0*  
*Status: Production Ready*
