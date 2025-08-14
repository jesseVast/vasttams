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

The TAMS API is built using FastAPI, a modern, fast web framework for building APIs with Python 3.7+ based on standard Python type hints.

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
└── storage/             # Storage layer abstractions
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
- **Business Rules**: Custom business logic validation
- **Data Integrity**: Referential integrity checks
- **Audit Trail**: Complete operation logging

### **4. Storage Layer**

The storage layer provides abstraction over multiple storage backends with intelligent caching and optimization.

#### **VAST Database (Metadata)**

VAST Database serves as the primary metadata store, providing:
- **High Performance**: Sub-second query response times
- **Scalability**: Petabyte-scale data handling
- **Time-Series Optimization**: Native time-series data support
- **Column Management**: Dynamic schema evolution

**Architecture:**
```
app/storage/vastdbmanager/
├── core.py                  # Main orchestrator
├── cache/                   # Intelligent caching system
├── queries/                 # Query processing & optimization
├── analytics/               # Advanced analytics capabilities
└── endpoints/               # Multi-endpoint management
```

#### **S3-Compatible Storage (Media Objects)**

S3-compatible storage handles the actual media file storage:
- **Object Storage**: Efficient binary data storage
- **Metadata Integration**: Seamless metadata-object linking
- **Multi-Provider Support**: AWS S3, MinIO, etc.
- **Lifecycle Management**: Automatic cleanup and optimization

### **5. Analytics Engine**

The analytics engine provides advanced data analysis capabilities using a hybrid approach.

**Hybrid Architecture:**
- **VAST for Filtering**: Efficient data extraction using predicates
- **DuckDB for Processing**: Advanced SQL analytics on filtered data
- **Memory Efficiency**: Only load relevant data for analysis
- **Real-Time Processing**: Stream processing capabilities

**Analytics Types:**
- **Time-Series Analytics**: Moving averages, trends, anomalies
- **Aggregation Analytics**: Percentiles, correlations, distributions
- **Performance Analytics**: Query performance and optimization
- **Business Analytics**: Usage patterns and insights

## 🔄 **Data Flow**

### **1. Media Upload Flow**

```
1. Client Request → API Layer
2. Authentication & Authorization
3. Business Logic Validation
4. Metadata Storage (VAST)
5. Object Storage (S3)
6. Response to Client
```

### **2. Media Retrieval Flow**

```
1. Client Request → API Layer
2. Authentication & Authorization
3. Metadata Query (VAST)
4. Object Retrieval (S3)
5. Response Assembly
6. Response to Client
```

### **3. Analytics Flow**

```
1. Analytics Request → API Layer
2. Authentication & Authorization
3. Data Filtering (VAST)
4. Data Processing (DuckDB)
5. Results Aggregation
6. Response to Client
```

## 📊 **Performance Characteristics**

### **Throughput**
- **API Requests**: 10,000+ requests/second
- **Data Ingestion**: 1GB+ per second
- **Query Performance**: Sub-second response times
- **Concurrent Users**: 1,000+ simultaneous users

### **Scalability**
- **Horizontal Scaling**: Stateless API instances
- **Database Scaling**: VAST cluster scaling
- **Storage Scaling**: S3-compatible storage scaling
- **Cache Scaling**: Distributed caching support

### **Reliability**
- **High Availability**: 99.9% uptime target
- **Data Durability**: 99.999999999% (11 9's)
- **Fault Tolerance**: Automatic failover
- **Backup & Recovery**: Automated backup procedures

## 🔒 **Security Architecture**

### **Network Security**
- **TLS/SSL**: End-to-end encryption
- **Firewall Rules**: Restrictive network access
- **VPC/Private Networks**: Isolated network segments
- **API Gateway**: Centralized security controls

### **Data Security**
- **Encryption at Rest**: AES-256 encryption
- **Encryption in Transit**: TLS 1.3
- **Access Controls**: Role-based access control
- **Audit Logging**: Complete access logging

### **Application Security**
- **Input Validation**: Comprehensive input sanitization
- **SQL Injection Protection**: Parameterized queries
- **XSS Protection**: Output encoding
- **Rate Limiting**: DDoS protection

## 🚀 **Deployment Architecture**

### **Containerization**
- **Docker**: Application containerization
- **Multi-Stage Builds**: Optimized image sizes
- **Health Checks**: Application health monitoring
- **Resource Limits**: CPU and memory constraints

### **Orchestration**
- **Kubernetes**: Container orchestration
- **Helm Charts**: Deployment templating
- **Service Mesh**: Inter-service communication
- **Auto-Scaling**: Dynamic resource allocation

### **Monitoring & Observability**
- **Prometheus**: Metrics collection
- **Grafana**: Visualization and dashboards
- **Jaeger**: Distributed tracing
- **ELK Stack**: Log aggregation and analysis

## 🔮 **Future Architecture**

### **Planned Enhancements**
- **GraphQL API**: Flexible query interface
- **Real-Time Streaming**: WebSocket support
- **Machine Learning**: AI-powered analytics
- **Edge Computing**: Distributed processing

### **Technology Evolution**
- **Database**: Advanced VAST features
- **Storage**: Object storage optimization
- **Analytics**: Real-time processing
- **Security**: Advanced threat protection

## 📚 **Architecture Principles**

### **Design Principles**
1. **Separation of Concerns**: Clear component boundaries
2. **Single Responsibility**: Each component has one purpose
3. **Open/Closed**: Open for extension, closed for modification
4. **Dependency Inversion**: Depend on abstractions, not concretions

### **Performance Principles**
1. **Caching First**: Cache everything possible
2. **Async Operations**: Non-blocking operations
3. **Batch Processing**: Efficient bulk operations
4. **Resource Optimization**: Minimal resource usage

### **Security Principles**
1. **Defense in Depth**: Multiple security layers
2. **Least Privilege**: Minimal required access
3. **Zero Trust**: Verify everything
4. **Security by Design**: Built-in security features
