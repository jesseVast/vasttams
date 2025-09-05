# TAMS Architecture Guide

This document provides detailed technical information about the TAMS API architecture, including modular design, storage systems, and implementation details.

## 🏗️ Architecture Overview

The TAMS API is built using a modern, modular architecture that separates concerns and provides clear interfaces between components.

<img width="822" height="430" alt="TAMS_Architecture-Live_white" src="https://github.com/user-attachments/assets/23ea1987-4b30-468f-89e4-a9a3778a2a02" />

## 🔧 Modular Router Architecture

The application follows a clean modular architecture with separate routers for each domain:

### Core Application Structure

- **`main.py`**: Core application setup, lifespan management, and service endpoints
- **`flows_router.py`**: Flow management endpoints (CRUD operations)
- **`segments_router.py`**: Flow segment management and media upload/download
- **`sources_router.py`**: Source management endpoints (CRUD operations)
- **`objects_router.py`**: Media object management
- **`analytics_router.py`**: Analytics and reporting endpoints
- **`dependencies.py`**: Dependency injection for VAST store access

### Router Responsibilities

Each router handles a specific domain and provides:

- **CRUD Operations**: Create, Read, Update, Delete operations
- **Input Validation**: Pydantic model validation for all inputs
- **Error Handling**: Consistent error responses and status codes
- **Business Logic**: Domain-specific business rules and validation
- **Response Formatting**: Consistent JSON response structures

### Dependency Injection

The application uses FastAPI's dependency injection system:

```python
# Example dependency injection
@router.get("/flows/{flow_id}")
async def get_flow(
    flow_id: str,
    store: VASTStore = Depends(get_vast_store)
) -> Flow:
    return await store.get_flow(flow_id)
```

## 💾 Hybrid Storage Architecture

The application uses a hybrid storage approach that combines the strengths of different storage systems:

### VAST Database Store

The application uses the `vastdbmanager.py` module to provide a clean interface to VAST Database:

#### **Columnar Storage**
- Apache Arrow schemas with optimized table structures
- Time-series optimization for media flow segments
- Vectorized operations for analytics
- Soft delete support with automatic filtering

#### **Transaction Support**
The vastdbmanager provides transaction support:

```python
with vast_store.db_manager.session.transaction() as tx:
    bucket = tx.bucket("tams-bucket")
    schema = bucket.schema("tams-schema")
    table = schema.table("sources")
    # Perform operations within transaction
```

#### **Schema Management**
- Automatic table creation and schema discovery
- Optimized schemas for TAMS data types
- Schema versioning and migration support
- Table statistics and performance monitoring

#### **Analytics Integration**
Built-in analytics queries:

```python
# Flow usage analytics
analytics = await store.analytics_query("flow_usage")

# Storage usage analytics  
analytics = await store.analytics_query("storage_usage")

# Time range analysis
analytics = await store.analytics_query("time_range_analysis")

# Catalog summary
analytics = await store.analytics_query("catalog_summary")
```

### S3 Store Integration

The `s3_store.py` module provides:

#### **Media Segment Storage**
```python
# Store flow segment
success = await s3_store.store_flow_segment(
    flow_id="flow-123",
    segment=flow_segment,
    data=media_bytes,
    content_type="video/mp4"
)

# Retrieve flow segment
data = await s3_store.get_flow_segment_data(
    flow_id="flow-123",
    segment_id="seg-001",
    timerange="[0:0_10:0)"
)

# Generate presigned URL
url = await s3_store.generate_presigned_url(
    flow_id="flow-123",
    segment_id="seg-001",
    timerange="[0:0_10:0)",
    operation="get_object",
    expires_in=3600
)
```

#### **Key Features**
- **Media Segment Storage**: Efficient storage of large media files
- **Presigned URLs**: Secure, time-limited access to media segments
- **Hierarchical Organization**: Year/month/day based storage structure
- **Metadata Tracking**: Comprehensive metadata for each segment
- **Multi-format Support**: Handles bytes, file paths, and file-like objects
- **Dual URL Support**: Separate URLs for GET and HEAD operations

### Storage Architecture Benefits

1. **Performance**: VAST database optimized for time-series queries
2. **Scalability**: S3 provides unlimited storage for media content
3. **Cost Efficiency**: Metadata in fast database, media in cost-effective S3
4. **Flexibility**: Support for multiple S3-compatible backends
5. **Reliability**: Redundant storage with automatic failover

## 🗄️ Database Schema

The VAST store creates the following tables with optimized schemas:

### Core Tables

#### **sources**
Media sources with metadata and collections:
```sql
id: string                    -- Unique source identifier
format: string               -- Content format URN
label: string                -- Human-readable label
description: string          -- Detailed description
created_by: string           -- User who created the source
updated_by: string           -- User who last updated
created: timestamp[us]       -- Creation timestamp
updated: timestamp[us]       -- Last update timestamp
tags: string                 -- JSON tags for categorization
source_collection: string    -- Collection grouping
collected_by: string         -- Collection method
deleted: bool                -- Soft delete flag
deleted_at: timestamp[us]    -- Deletion timestamp
deleted_by: string           -- User who deleted
```

#### **flows**
Media flows with format-specific attributes:
```sql
id: string                    -- Unique flow identifier
source_id: string            -- Reference to source
format: string               -- Content format URN
codec: string                -- Media codec information
label: string                -- Human-readable label
description: string          -- Detailed description
created_by: string           -- User who created the flow
updated_by: string           -- User who last updated
created: timestamp[us]       -- Creation timestamp
updated: timestamp[us]       -- Last update timestamp
tags: string                 -- JSON tags for categorization
container: string            -- Media container format
read_only: bool              -- Read-only flag
frame_width: int32           -- Video frame width
frame_height: int32          -- Video frame height
frame_rate: string           -- Video frame rate
interlace_mode: string       -- Video interlace mode
color_sampling: string       -- Video color sampling
color_space: string          -- Video color space
transfer_characteristics: string -- Video transfer characteristics
color_primaries: string      -- Video color primaries
sample_rate: int32           -- Audio sample rate
bits_per_sample: int32       -- Audio bits per sample
channels: int32              -- Audio channel count
flow_collection: string      -- MultiFlow collection
deleted: bool                -- Soft delete flag
deleted_at: timestamp[us]    -- Deletion timestamp
deleted_by: string           -- User who deleted
```

#### **segments**
Time-series optimized flow segments:
```sql
id: string                    -- Unique segment identifier
flow_id: string              -- Reference to flow
object_id: string            -- Reference to media object
timerange: string            -- Time range specification
ts_offset: string            -- Timestamp offset
last_duration: string        -- Duration of last sample
sample_offset: int64         -- Starting sample offset
sample_count: int64          -- Number of samples
get_urls: string             -- JSON array of access URLs
key_frame_count: int32       -- Number of key frames
created: timestamp[us]       -- Creation timestamp
start_time: timestamp[us]    -- Segment start time
end_time: timestamp[us]      -- Segment end time
duration_seconds: double     -- Segment duration
tags: string                 -- JSON tags for categorization (6.0p4+)
deleted: bool                -- Soft delete flag
deleted_at: timestamp[us]    -- Deletion timestamp
deleted_by: string           -- User who deleted
```

#### **objects**
Media objects with access tracking:
```sql
object_id: string            -- Unique object identifier
flow_references: string      -- JSON array of flow references
size: int64                  -- Object size in bytes
created: timestamp[us]       -- Creation timestamp
last_accessed: timestamp[us] -- Last access timestamp
access_count: int32          -- Access counter
deleted: bool                -- Soft delete flag
deleted_at: timestamp[us]    -- Deletion timestamp
deleted_by: string           -- User who deleted
```

#### **webhooks**
Event notification configuration:
```sql
id: string                    -- Unique webhook identifier
url: string                   -- Webhook endpoint URL
api_key_name: string          -- API key header name
api_key_value: string         -- API key value
events: string                -- JSON array of event types
owner_id: string              -- Webhook owner
created_by: string            -- User who created
created: timestamp[us]        -- Creation timestamp
updated: timestamp[us]        -- Last update timestamp
```

#### **deletion_requests**
Media deletion tracking:
```sql
id: string                    -- Unique request identifier
flow_id: string              -- Reference to flow
timerange: string            -- Time range for deletion
status: string               -- Request status
created: timestamp[us]       -- Creation timestamp
updated: timestamp[us]       -- Last update timestamp
```

### Soft Delete Schema Fields

All tables include additional soft delete fields for data integrity:

```json
{
  "deleted": false,           // Boolean flag indicating soft-deleted state
  "deleted_at": null,         // ISO 8601 timestamp of deletion
  "deleted_by": null          // String identifier of user/system that performed deletion
}
```

**Important**: Soft-deleted records are automatically excluded from all query operations to maintain data consistency.

## 🏷️ Tag Architecture (6.0p4+)

### Unified Tag Storage

As of release 6.0p4, TAMS uses a unified column-based tag architecture across all resource types:

#### **Column-Based Approach**
- **Sources**: Tags stored in `sources.tags` column as JSON string
- **Flows**: Tags stored in `flows.tags` column as JSON string  
- **Segments**: Tags stored in `segments.tags` column as JSON string

#### **Benefits of Unified Architecture**
1. **Consistency**: All resources use the same tag storage mechanism
2. **Performance**: Database-level filtering with `ibis_.tags.contains()` queries
3. **Simplicity**: No separate table management required
4. **Maintainability**: Single source of truth for tag data

#### **Tag Query Capabilities**
- **Value-based Filtering**: `tag.{name}=value` for exact matches
- **Existence-based Filtering**: `tag_exists.{name}=true/false` for tag presence
- **JSON Querying**: Efficient `ibis_.tags.contains()` for database-level filtering
- **Cross-Resource**: Consistent query syntax across all resource types

#### **Migration from Separate Tables**
- **Previous Architecture**: Segments used separate `segment_tags` table
- **Current Architecture**: All resources use column-based tag storage
- **Database Cleanup**: Old `segment_tags` table removed during migration
- **Backward Compatibility**: API endpoints remain unchanged

## 🔄 Data Flow Architecture

### Segment Creation Flow

1. **Client Request**: Client sends segment creation request
2. **Validation**: Input validation using Pydantic models
3. **Business Logic**: Business rule validation and processing
4. **Storage Operations**:
   - **Metadata**: Stored in VAST database
   - **Media Content**: Stored in S3 (if provided)
   - **Object Management**: Object created/updated automatically
5. **URL Generation**: Pre-signed URLs generated for both GET and HEAD operations
6. **Response**: Segment information with access URLs returned

### Media Access Flow

1. **Client Request**: Client requests segment information
2. **Metadata Retrieval**: Segment metadata retrieved from VAST database
3. **URL Generation**: Fresh pre-signed URLs generated for S3 access
4. **Response**: Segment data with access URLs returned
5. **Direct Access**: Client uses URLs to access S3 content directly

### Object Reuse Flow

1. **Segment Creation**: Multiple segments reference same object ID
2. **Object Lookup**: System checks if object exists
3. **Flow Reference Update**: New flow reference added to existing object
4. **URL Generation**: URLs generated for all referencing segments
5. **Efficient Storage**: Single media file serves multiple time ranges

## 🚀 Performance Optimizations

### Time-Series Optimization

- **Automatic Indexing**: Time-based queries automatically optimized
- **Range Queries**: Efficient timerange filtering and pagination
- **Batch Operations**: Multiple segments processed in single transaction
- **Lazy Loading**: Media content loaded only when requested

### Storage Optimization

- **Hierarchical Organization**: S3 keys organized by date for efficient access
- **Metadata Caching**: Frequently accessed metadata cached in memory
- **Connection Pooling**: Database connections reused efficiently
- **Async Operations**: Non-blocking I/O for improved throughput

### Query Optimization

- **Predicate Pushdown**: Filters applied at storage level
- **Columnar Access**: Only required columns loaded for queries
- **Parallel Processing**: Multiple queries executed concurrently
- **Result Streaming**: Large result sets streamed efficiently

## 🔒 Security Architecture

### Authentication & Authorization

- **API Key Authentication**: Webhook endpoints use API key authentication
- **Database Authentication**: VAST database access with access key/secret
- **S3 Authentication**: S3 operations with access key/secret
- **No User Authentication**: OAuth2/JWT not implemented (see roadmap)

### Data Security

- **Input Validation**: All inputs validated with Pydantic models
- **SQL Injection Protection**: Parameterized queries prevent injection
- **XSS Protection**: Output sanitization prevents cross-site scripting
- **Soft Delete**: Data safety with audit trails and recovery capabilities

### Network Security

- **HTTPS Support**: TLS encryption for secure communications
- **CORS Configuration**: Configurable cross-origin resource sharing
- **Rate Limiting**: Configurable request rate limiting
- **Security Headers**: Configurable security header enforcement

## 📊 Observability Architecture

### Telemetry System

- **Prometheus Metrics**: HTTP, business, performance, and system metrics
- **OpenTelemetry Tracing**: Distributed tracing with correlation IDs
- **Structured Logging**: JSON logging with telemetry context
- **Health Checks**: System metrics and dependency health

### Monitoring Components

- **Metrics Collection**: Real-time metrics collection and aggregation
- **Alerting**: Configurable alerts for critical metrics
- **Dashboards**: Pre-configured Grafana dashboards
- **Tracing**: Request tracking across services with Jaeger integration

### Performance Monitoring

- **VAST Database**: Query performance and connection monitoring
- **S3 Operations**: Storage operation performance tracking
- **API Endpoints**: Response time and throughput monitoring
- **Business Metrics**: Sources, flows, segments, and storage usage analytics

## 🔧 Configuration Management

### Environment Configuration

The application uses a centralized configuration system:

```python
# Configuration structure
class Settings(BaseSettings):
    # Server settings
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    
    # VAST Database settings
    vast_endpoint: str
    vast_access_key: str
    vast_secret_key: str
    vast_bucket: str
    vast_schema: str
    
    # S3 Storage settings
    s3_endpoint_url: str
    s3_access_key_id: str
    s3_secret_access_key: str
    s3_bucket_name: str
    s3_use_ssl: bool = True
    
    # Logging
    log_level: str = "INFO"
    
    # Security
    secret_key: str
```

### Configuration Sources

1. **Environment Variables**: Primary configuration source
2. **Configuration Files**: Optional JSON configuration files
3. **Default Values**: Sensible defaults for development
4. **Validation**: Configuration validation on startup

## 🧪 Testing Architecture

### Test Organization

- **Unit Tests**: Isolated component testing with mocked dependencies
- **Integration Tests**: End-to-end testing with real database and S3
- **API Tests**: HTTP API testing with request/response validation
- **Performance Tests**: Load testing and performance benchmarking

### Test Infrastructure

- **Test Database**: Isolated VAST database instance for testing
- **Test S3**: Isolated S3-compatible storage for testing
- **Mock Services**: Mock external services for unit testing
- **Test Data**: Comprehensive test data sets for validation

### Test Coverage

- **CRUD Operations**: All create, read, update, delete operations
- **Business Logic**: Business rule validation and edge cases
- **Error Handling**: Error scenarios and exception handling
- **Performance**: Response time and throughput validation
- **Security**: Input validation and security testing

## 🚀 Deployment Architecture

### Container Architecture

- **Application Container**: FastAPI application with Python runtime
- **Database Container**: VAST database instance
- **Storage Container**: S3-compatible storage (MinIO)
- **Observability Stack**: Prometheus, Grafana, Jaeger

### Kubernetes Architecture

- **Deployment**: Application deployment with health checks
- **Services**: Internal and external service exposure
- **Ingress**: HTTP routing and load balancing
- **ConfigMaps**: Configuration management
- **Secrets**: Secure credential storage
- **Persistent Volumes**: Data persistence for database and storage

### Scaling Architecture

- **Horizontal Scaling**: Multiple application instances
- **Load Balancing**: Request distribution across instances
- **Auto-scaling**: Automatic scaling based on metrics
- **Database Scaling**: Read replicas and connection pooling
- **Storage Scaling**: S3-compatible storage auto-scaling

## 🔮 Future Architecture Enhancements

### Planned Improvements

- **Microservices**: Break down into smaller, focused services
- **Event Sourcing**: Event-driven architecture for better scalability
- **CQRS**: Command Query Responsibility Segregation
- **GraphQL**: Alternative API interface for complex queries
- **Service Mesh**: Istio or Linkerd for service-to-service communication

### Performance Enhancements

- **Caching Layer**: Redis or Memcached for metadata caching
- **CDN Integration**: Content delivery network for media content
- **Database Sharding**: Horizontal database partitioning
- **Async Processing**: Background job processing for heavy operations
- **Streaming**: Real-time data streaming capabilities

### Security Enhancements

- **OAuth2/JWT**: User authentication and authorization
- **RBAC**: Role-based access control
- **API Gateway**: Centralized API management and security
- **Audit Logging**: Comprehensive audit trail
- **Encryption**: End-to-end encryption for sensitive data

## 📚 Additional Resources

- **[Usage Guide](USAGE.md)** - Comprehensive usage examples and patterns
- **[API Reference](API_REFERENCE.md)** - Complete API endpoint documentation
- **[Deployment Guide](DEPLOYMENT.md)** - Deployment and configuration details
- **[Observability Guide](OBSERVABILITY.md)** - Monitoring and observability setup
- **[Soft Delete Extension](SOFT_DELETE_EXTENSION.md)** - Soft delete functionality details
