# TAMS Architecture Documentation

This document provides an overview of the TAMS (Time-addressable Media Store) API system architecture.

## 🏗️ **System Overview**

TAMS is a high-performance, scalable media storage and management system built on modern cloud-native technologies. The system is designed to handle large volumes of time-series media data with efficient storage, retrieval, and analytics capabilities.

## 🏛️ **High-Level Architecture**

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Client Apps   │    │   Web Browser   │    │   Mobile Apps   │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                    ┌─────────────▼─────────────┐
                    │      Load Balancer       │
                    │      (Nginx/HAProxy)     │
                    └─────────────┬─────────────┘
                                 │
                    ┌─────────────▼─────────────┐
                    │      TAMS API Layer      │
                    │    (FastAPI + Uvicorn)   │
                    └─────────────┬─────────────┘
                                 │
          ┌──────────────────────┼──────────────────────┐
          │                      │                      │
┌─────────▼─────────┐  ┌─────────▼─────────┐  ┌─────────▼─────────┐
│   Authentication  │  │   Business Logic │  │   Data Access     │
│   & Authorization │  │   & Validation   │  │   & Storage       │
└───────────────────┘  └───────────────────┘  └───────────────────┘
                                 │
                    ┌─────────────▼─────────────┐
                    │      Storage Layer        │
                    │                           │
                    │  ┌─────────┐ ┌─────────┐ │
                    │  │ VAST DB │ │ S3/Obj │ │
                    │  │(Metadata)│ │Storage │ │
                    │  └─────────┘ └─────────┘ │
                    └───────────────────────────┘
```

## 🔧 **Core Components**

### **1. API Layer (FastAPI)**

The TAMS API is built using FastAPI, a modern, fast web framework for building APIs with Python 3.12+ based on standard Python type hints.

**Key Features:**
- **Automatic API Documentation**: OpenAPI/Swagger UI generation
- **Type Safety**: Full type checking and validation
- **High Performance**: Built on Starlette and Pydantic
- **Async Support**: Native async/await support
- **Dependency Injection**: Clean dependency management

**Architecture:**
```
app/
├── main.py              # FastAPI application entry point
├── api/                 # API route definitions
│   ├── sources_router.py
│   ├── flows_router.py
│   ├── segments_router.py
│   └── objects_router.py
├── auth/                # Authentication and authorization
├── core/                # Core application logic
├── models/              # Data models and schemas
└── storage/             # Enhanced storage layer architecture
```

### **2. Authentication & Authorization**

The system implements a comprehensive authentication and authorization system with multiple provider support.

**Providers:**
- **JWT**: JSON Web Token-based authentication
- **API Keys**: Simple API key authentication
- **Basic Auth**: Username/password authentication
- **URL Tokens**: Secure token-based authentication

**Security Features:**
- **Rate Limiting**: Configurable request rate limiting
- **Token Expiration**: Automatic token refresh and expiration
- **Audit Logging**: Complete authentication event logging
- **Role-Based Access**: Fine-grained permission control

### **3. Business Logic Layer**

The business logic layer handles all application-specific operations and business rules.

**Key Components:**
- **Source Management**: Media source creation, updates, and deletion
- **Flow Management**: Media flow processing and management
- **Segment Management**: Media segment handling and storage
- **Object Management**: Media object lifecycle management

**Validation:**
- **Input Validation**: Pydantic model validation
- **Business Rules**: Domain-specific validation logic
- **Data Integrity**: Referential integrity checks

### **4. Enhanced Storage Layer**

The storage layer has been completely refactored to provide better separation of concerns, improved debugging capabilities, and enhanced performance.

#### **4.1 Core Storage Modules**

**`s3_core.py`**: Pure S3 infrastructure code
- Connection management and configuration
- Bucket operations and lifecycle management
- Error handling and retry logic
- Performance optimization utilities

**`vast_core.py`**: Pure VAST database infrastructure code
- Connection pooling and management
- Query execution and optimization
- Schema management and validation
- Performance monitoring and metrics

**`storage_factory.py`**: Storage backend factory
- Dynamic storage backend selection
- Configuration-based backend instantiation
- Backend health monitoring and failover

#### **4.2 TAMS-Specific Storage Modules**

**`sources/`**: Source storage operations
- Source CRUD operations
- Source metadata management
- Source relationship handling

**`flows/`**: Flow storage operations
- Flow CRUD operations
- Flow metadata and attributes
- Flow-source relationships

**`segments/`**: Segment storage operations
- Segment CRUD operations
- Media data storage and retrieval
- Time range optimization

**`objects/`**: Object storage operations
- Object CRUD operations
- Object metadata management
- Access tracking and analytics

**`analytics/`**: Analytics storage operations
- Analytics data storage
- Query optimization for analytics
- Performance metrics collection

**`tags/`**: Tags storage operations
- Tag CRUD operations
- Tag relationship management
- Tag-based querying

#### **4.3 Diagnostics Module**

**`connection_tester.py`**: Connection health testing
- Network connectivity validation
- Endpoint health checks
- Performance benchmarking

**`health_monitor.py`**: System health monitoring
- Real-time health status
- Performance metrics collection
- Alert generation

**`logger.py`**: Enhanced logging system
- Structured logging with context
- Performance logging
- Error tracking and reporting

**`model_validator.py`**: Data validation utilities
- Schema validation
- Data integrity checks
- Error reporting and debugging

**`performance_analyzer.py`**: Performance analysis
- Query performance analysis
- Bottleneck identification
- Optimization recommendations

**`troubleshooter.py`**: Automated troubleshooting
- Common issue detection
- Solution recommendations
- Debug information collection

#### **4.4 Enhanced VAST Database Manager**

**`core.py`**: Main orchestrator
- High-level operation coordination
- Transaction management
- Error handling and recovery

**`cache/`**: Intelligent caching system
- TTL-based cache management
- Background cache updates
- Memory-efficient storage

**`queries/`**: Query processing & optimization
- Query parsing and validation
- Dynamic optimization strategies
- Performance monitoring

**`analytics/`**: Advanced analytics capabilities
- Time-series analysis
- Statistical aggregations
- Performance monitoring

**`endpoints/`**: Multi-endpoint management
- Load balancing
- Health monitoring
- Failover handling

### **5. Data Models and Validation**

The system uses Pydantic v2 for comprehensive data validation and serialization.

**Key Features:**
- **Type Safety**: Full type checking at runtime
- **Automatic Validation**: Schema-based validation
- **Serialization**: JSON serialization/deserialization
- **Documentation**: Automatic API documentation generation

**Model Structure:**
```
models/
├── base.py              # Base model classes
├── sources.py           # Source data models
├── flows.py             # Flow data models
├── segments.py          # Segment data models
├── objects.py           # Object data models
└── common.py            # Common data types
```

## 🗄️ **Storage Architecture**

### **Hybrid Storage Approach**

The system uses a hybrid storage approach combining the strengths of different storage technologies:

1. **VAST Database**: High-performance columnar storage for metadata and analytics
2. **S3-Compatible Storage**: Scalable object storage for media segments
3. **Intelligent Caching**: Multi-level caching for performance optimization

### **VAST Database Schema**

The VAST database uses optimized schemas for TAMS data types:

**Sources Table:**
```sql
CREATE TABLE sources (
    id VARCHAR PRIMARY KEY,
    format VARCHAR NOT NULL,
    label VARCHAR,
    description TEXT,
    tags JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    deleted BOOLEAN DEFAULT FALSE,
    deleted_at TIMESTAMP,
    deleted_by VARCHAR
);
```

**Flows Table:**
```sql
CREATE TABLE flows (
    id VARCHAR PRIMARY KEY,
    source_id VARCHAR REFERENCES sources(id),
    format VARCHAR NOT NULL,
    codec VARCHAR,
    frame_width INTEGER,
    frame_height INTEGER,
    frame_rate VARCHAR,
    label VARCHAR,
    description TEXT,
    tags JSONB,
    read_only BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    deleted BOOLEAN DEFAULT FALSE,
    deleted_at TIMESTAMP,
    deleted_by VARCHAR
);
```

**Segments Table:**
```sql
CREATE TABLE segments (
    id VARCHAR PRIMARY KEY,
    flow_id VARCHAR REFERENCES flows(id),
    object_id VARCHAR NOT NULL,
    timerange VARCHAR NOT NULL,
    sample_offset BIGINT DEFAULT 0,
    sample_count BIGINT,
    storage_path VARCHAR,
    file_size BIGINT,
    content_type VARCHAR,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    deleted BOOLEAN DEFAULT FALSE,
    deleted_at TIMESTAMP,
    deleted_by VARCHAR
);
```

### **S3 Storage Organization**

Media segments are organized in a hierarchical structure:

```
s3://bucket-name/
├── tams/
│   ├── 2024/
│   │   ├── 01/
│   │   │   ├── 15/
│   │   │   │   ├── flow-id-1/
│   │   │   │   │   ├── segment-001.mp4
│   │   │   │   │   └── segment-002.mp4
│   │   │   │   └── flow-id-2/
│   │   │   │       └── segment-001.mp4
│   │   │   └── 16/
│   │   └── 02/
│   └── 2025/
```

## 🔄 **Data Flow**

### **1. Media Upload Flow**

```
Client → API → Validation → Business Logic → Storage Layer
                                    ↓
                            ┌─────────────┬─────────────┐
                            │ VAST Store  │   S3 Store │
                            │ (Metadata)  │ (Media)    │
                            └─────────────┴─────────────┘
```

### **2. Media Retrieval Flow**

```
Client → API → Validation → Business Logic → Storage Layer
                                    ↓
                            ┌─────────────┬─────────────┐
                            │ VAST Store  │   S3 Store │
                            │ (Metadata)  │ (Media)    │
                            └─────────────┴─────────────┘
                                    ↓
                            Presigned URL Generation
                                    ↓
                            Client Download
```

### **3. Analytics Flow**

```
Client → API → Validation → Analytics Engine → VAST Store
                                    ↓
                            Query Optimization
                                    ↓
                            Data Processing
                                    ↓
                            Result Aggregation
                                    ↓
                            Response Generation
```

## 🚀 **Performance Optimizations**

### **1. Caching Strategy**

- **Multi-Level Caching**: Application, database, and CDN caching
- **TTL-Based Expiration**: Automatic cache invalidation
- **Background Updates**: Non-blocking cache refresh
- **Memory Management**: Configurable cache size limits

### **2. Query Optimization**

- **Dynamic Splits**: Automatic query splitting based on table size
- **Index Optimization**: Strategic index placement for common queries
- **Query Caching**: Result caching for repeated queries
- **Parallel Processing**: Concurrent query execution

### **3. Storage Optimization**

- **Compression**: Automatic data compression for media files
- **Deduplication**: Storage deduplication for identical segments
- **Lifecycle Management**: Automatic cleanup of old data
- **Load Balancing**: Intelligent storage backend selection

## 🔍 **Monitoring and Observability**

### **1. Metrics Collection**

- **Application Metrics**: Request rates, response times, error rates
- **Storage Metrics**: I/O operations, storage usage, performance
- **Business Metrics**: User activity, data growth, usage patterns
- **System Metrics**: CPU, memory, network, disk usage

### **2. Logging Strategy**

- **Structured Logging**: JSON-formatted logs with context
- **Log Levels**: Configurable logging verbosity
- **Log Aggregation**: Centralized log collection and analysis
- **Performance Logging**: Detailed performance metrics

### **3. Health Monitoring**

- **Endpoint Health**: Real-time health status of all components
- **Dependency Health**: Database, storage, and external service health
- **Performance Health**: Response time and throughput monitoring
- **Alert Generation**: Automatic alerting for critical issues

## 🔒 **Security Architecture**

### **1. Authentication**

- **Multi-Provider Support**: JWT, API keys, basic auth, URL tokens
- **Token Management**: Secure token generation and validation
- **Session Management**: Secure session handling and expiration
- **Rate Limiting**: Protection against abuse and attacks

### **2. Authorization**

- **Role-Based Access Control**: Fine-grained permission management
- **Resource-Level Security**: Per-resource access control
- **Audit Logging**: Complete access and modification logging
- **Data Encryption**: Encryption at rest and in transit

### **3. Data Protection**

- **Soft Delete**: Data safety with audit trails
- **Access Logging**: Complete access history tracking
- **Data Validation**: Comprehensive input validation
- **Error Handling**: Secure error message generation

## 🚀 **Scalability Features**

### **1. Horizontal Scaling**

- **Load Balancing**: Automatic request distribution
- **Stateless Design**: No server-side state dependencies
- **Database Sharding**: Horizontal database scaling
- **Storage Distribution**: Multi-region storage support

### **2. Performance Scaling**

- **Connection Pooling**: Efficient database connection management
- **Query Optimization**: Dynamic query performance tuning
- **Caching Layers**: Multi-level performance optimization
- **Background Processing**: Asynchronous operation handling

### **3. Storage Scaling**

- **Object Storage**: Unlimited storage capacity
- **CDN Integration**: Global content delivery
- **Compression**: Storage space optimization
- **Lifecycle Management**: Automatic data lifecycle handling

## 🔧 **Deployment Architecture**

### **1. Container Deployment**

- **Docker Support**: Complete containerization
- **Multi-Stage Builds**: Optimized image creation
- **Environment Configuration**: Flexible configuration management
- **Health Checks**: Built-in health monitoring

### **2. Kubernetes Deployment**

- **Complete K8s Manifests**: Production-ready deployment
- **Horizontal Pod Autoscaling**: Automatic scaling
- **Service Mesh Ready**: Istio/Linkerd compatibility
- **Monitoring Integration**: Prometheus and Grafana integration

### **3. Observability Stack**

- **Prometheus**: Metrics collection and storage
- **Grafana**: Visualization and dashboards
- **Jaeger**: Distributed tracing
- **Alertmanager**: Alert management and routing

## 📊 **Analytics and Reporting**

### **1. Built-in Analytics**

- **Flow Usage Analytics**: Usage patterns and statistics
- **Storage Analytics**: Storage usage and optimization
- **Time Range Analysis**: Temporal data analysis
- **Performance Analytics**: System performance metrics

### **2. Custom Analytics**

- **Query Interface**: Custom analytics queries
- **Data Export**: Analytics data export capabilities
- **Real-time Dashboards**: Live monitoring dashboards
- **Alert Generation**: Automated alerting based on analytics

### **3. Business Intelligence**

- **Usage Patterns**: User behavior analysis
- **Capacity Planning**: Resource usage forecasting
- **Performance Optimization**: System optimization recommendations
- **Cost Analysis**: Storage and compute cost analysis

This architecture provides a robust, scalable, and maintainable foundation for the TAMS API system, with clear separation of concerns, comprehensive monitoring, and excellent performance characteristics.
