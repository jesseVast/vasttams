# TAMS Development Documentation

This document consolidates all development-related information for the TAMS (Time-addressable Media Store) API.

## 🚀 **Current Project Status**

### **What We've Accomplished**

#### **1. Complete Modular Refactoring** ✅
- **Broke down monolithic `vastdbmanager.py`** (1600+ lines) into focused, maintainable modules
- **Created clean separation of concerns** with single responsibility principle
- **Maintained backward compatibility** while adding powerful new features

#### **2. Enhanced Storage Architecture** 🏗️
```
app/storage/
├── __init__.py              # Main module exports
├── core/                    # Core storage infrastructure
│   ├── __init__.py
│   ├── s3_core.py          # S3 infrastructure only
│   ├── vast_core.py        # VAST infrastructure only
│   └── storage_factory.py  # Backend factory
├── endpoints/               # TAMS-specific storage operations
│   ├── sources/            # Source storage operations
│   ├── flows/              # Flow storage operations
│   ├── segments/           # Segment storage operations
│   ├── objects/            # Object storage operations
│   ├── analytics/          # Analytics storage operations
│   └── tags/               # Tags storage operations
├── diagnostics/             # Comprehensive diagnostics
│   ├── connection_tester.py
│   ├── health_monitor.py
│   ├── logger.py
│   ├── model_validator.py
│   ├── performance_analyzer.py
│   └── troubleshooter.py
├── vastdbmanager/           # Enhanced VAST database manager
│   ├── core.py             # Main orchestrator
│   ├── cache/              # Intelligent caching system
│   ├── queries/            # Query processing & optimization
│   ├── analytics/          # Advanced analytics capabilities
│   └── endpoints/          # Multi-endpoint management
├── vast_store.py            # VAST database store
├── s3_store.py              # S3 storage manager
└── schemas.py               # Storage schemas
```

#### **3. Advanced Analytics & Monitoring** 📊

##### **Real-Time Analytics**
- **Moving Averages**: Time-windowed calculations with configurable periods
- **Trend Analysis**: Linear regression approximation for time-series data
- **Anomaly Detection**: Statistical outlier detection using z-scores
- **Window Functions**: Advanced time-based aggregations

##### **Advanced Aggregation Analytics**
- **Percentile Calculations**: P25, P50, P75, P90, P95, P99 with DuckDB
- **Correlation Analysis**: Statistical correlation between columns
- **Distribution Analysis**: Histogram generation with custom binning
- **Top-N Analysis**: Ranked aggregations by group

##### **Performance Monitoring**
- **Query Metrics**: Execution times, row counts, splits utilization
- **Slow Query Detection**: Automatic identification of performance issues
- **Performance Trends**: Historical analysis and capacity planning
- **Export Capabilities**: Metrics export for external analysis

##### **Operational Intelligence**
- **Endpoint Health**: Real-time monitoring of VAST cluster nodes
- **Load Balancing**: Intelligent routing based on operation type and performance
- **Cache Analytics**: Hit rates, expiration tracking, memory usage
- **System Health**: Comprehensive health checks and status reporting

#### **4. Hybrid Analytics Architecture** 🦆
- **VAST for Filtering**: Efficient data extraction using predicates
- **DuckDB for Processing**: Advanced SQL analytics on filtered data
- **Memory Efficiency**: Only load relevant data into DuckDB
- **Best of Both Worlds**: Performance + functionality

#### **5. Enhanced Performance Features** ⚡
- **Intelligent Caching**: TTL-based cache with background updates
- **Query Optimization**: Dynamic splits/subsplits based on table size
- **Load Balancing**: Performance-based endpoint selection
- **Background Processing**: Non-blocking cache and stats updates

### **Technical Implementation Details**

#### **Cache System**
- **Thread-Safe**: RLock-based concurrent access
- **TTL Management**: Automatic expiration with configurable timeouts
- **Background Updates**: Periodic refresh without blocking operations
- **Memory Efficient**: Configurable cache size limits

#### **Query Optimization**
- **Dynamic Configuration**: Auto-calculate splits based on table characteristics
- **Type-Specific Tuning**: Different optimizations for time-series vs aggregation
- **Memory Management**: Adjust row limits for small tables
- **Performance Monitoring**: Track optimization effectiveness

#### **Endpoint Management**
- **Health Monitoring**: Track response times and error rates
- **Automatic Failover**: Mark endpoints unhealthy after multiple failures
- **Load Distribution**: Round-robin and performance-based routing
- **Statistics Collection**: Comprehensive endpoint performance metrics

#### **Analytics Engine**
- **Modular Design**: Easy to add new analytical functions
- **Error Handling**: Robust error handling with detailed logging
- **Performance Optimization**: Automatic query optimization
- **Memory Management**: Efficient memory usage for large datasets

## 🛠️ **Development Environment Setup**

### **Prerequisites**
- **Python 3.12+**: Required for modern language features and performance
- **VAST Database**: For development and testing
- **S3-Compatible Storage**: MinIO, AWS S3, or VAST S3
- **Docker**: For containerized development (optional)

### **Local Development Setup**

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd bbctams
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt  # Development dependencies
   ```

4. **Environment configuration**
   ```bash
   cp env.example .env
   # Edit .env with your configuration
   ```

5. **Run the application**
   ```bash
   python run.py
   # Or use uvicorn directly
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

### **Docker Development Setup**

1. **Build and run with Docker Compose**
   ```bash
   cd docker
   docker-compose up --build
   ```

2. **Development with hot reload**
   ```bash
   docker-compose -f docker-compose.dev.yml up --build
   ```

## 🧪 **Testing Strategy**

### **Test Structure**
```
tests/
├── conftest.py                    # Test configuration and fixtures
├── pytest.ini                     # Pytest configuration
├── test_api/                      # API endpoint tests
├── test_core/                     # Core functionality tests
├── test_integration/              # Integration tests
├── test_storage/                  # Storage layer tests
└── test_utils/                    # Utility function tests
```

### **Test Types**

#### **Unit Tests**
- **Purpose**: Test individual functions and classes in isolation
- **Dependencies**: Mocked external dependencies
- **Coverage**: All business logic and utility functions
- **Execution**: Fast, reliable, and repeatable

#### **Integration Tests**
- **Purpose**: Test component interactions and data flow
- **Dependencies**: Real database and storage connections
- **Coverage**: End-to-end workflows and error scenarios
- **Execution**: Slower but comprehensive validation

#### **API Tests**
- **Purpose**: Test HTTP endpoints and request/response handling
- **Dependencies**: Running API server
- **Coverage**: All API endpoints and error conditions
- **Execution**: HTTP-level validation

### **Running Tests**

#### **All Tests**
```bash
pytest tests/
```

#### **Specific Test Categories**
```bash
# Unit tests only
pytest tests/ -m "not integration"

# Integration tests only
pytest tests/ -m "integration"

# API tests only
pytest tests/test_api/

# Storage tests only
pytest tests/test_storage/
```

#### **Test with Coverage**
```bash
pytest tests/ --cov=app --cov-report=html
```

#### **Performance Tests**
```bash
# Run performance benchmarks
pytest tests/test_performance/ -v

# Run with performance profiling
pytest tests/test_performance/ --profile
```

### **Test Data Management**

#### **Test Data Generation**
```bash
# Generate test data for development
python mgmt/generate_test_data.py

# Generate specific data types
python mgmt/generate_test_data.py --type=flows --count=100
```

#### **Database Cleanup**
```bash
# Clean up test data
python mgmt/cleanup_database.py

# Reset specific tables
python mgmt/cleanup_database.py --tables=sources,flows
```

## 🔧 **Development Workflow**

### **Code Quality Standards**

#### **Python Code Style**
- **PEP 8**: Standard Python style guide
- **Type Hints**: All functions must have type annotations
- **Docstrings**: Comprehensive docstrings for all public functions
- **Error Handling**: Proper exception handling and logging

#### **Code Organization**
- **Single Responsibility**: Each module has one clear purpose
- **Dependency Injection**: Use dependency injection for external dependencies
- **Interface Segregation**: Keep interfaces focused and minimal
- **Open/Closed**: Open for extension, closed for modification

### **Development Process**

1. **Feature Development**
   - Create feature branch from main
   - Implement feature with tests
   - Update documentation
   - Create pull request

2. **Code Review**
   - Automated testing and linting
   - Manual code review
   - Performance and security review
   - Documentation review

3. **Integration**
   - Merge to main branch
   - Run full test suite
   - Update version and changelog
   - Deploy to staging environment

### **Debugging and Troubleshooting**

#### **Local Debugging**
```bash
# Run with debug logging
LOG_LEVEL=DEBUG python run.py

# Run with specific debug modules
LOG_LEVEL=DEBUG python -c "import logging; logging.getLogger('app.storage').setLevel(logging.DEBUG)"
```

#### **Diagnostic Tools**
```bash
# Test storage connections
python mgmt/test_diagnostics.py

# Check database health
python mgmt/test_diagnostics.py --check=db

# Validate data models
python mgmt/test_diagnostics.py --check=models
```

#### **Performance Profiling**
```bash
# Profile specific functions
python -m cProfile -o profile.stats app/main.py

# Analyze profile results
python -c "import pstats; p = pstats.Stats('profile.stats'); p.sort_stats('cumulative').print_stats(20)"
```

## 📚 **API Development**

### **Adding New Endpoints**

1. **Create Router Module**
   ```python
   # app/api/new_feature_router.py
   from fastapi import APIRouter, Depends
   from app.storage.endpoints.new_feature import NewFeatureStorage
   
   router = APIRouter(prefix="/new-feature", tags=["new-feature"])
   
   @router.get("/")
   async def list_new_features(storage: NewFeatureStorage = Depends()):
       return await storage.list_new_features()
   ```

2. **Create Storage Module**
   ```python
   # app/storage/endpoints/new_feature/new_feature_storage.py
   from app.storage.core.vast_core import VastCore
   
   class NewFeatureStorage:
       def __init__(self, vast_core: VastCore):
           self.vast_core = vast_core
       
       async def list_new_features(self):
           # Implementation
           pass
   ```

3. **Register Router**
   ```python
   # app/main.py
   from app.api.new_feature_router import router as new_feature_router
   
   app.include_router(new_feature_router)
   ```

4. **Add Tests**
   ```python
   # tests/test_api/test_new_feature.py
   def test_list_new_features(client):
       response = client.get("/new-feature/")
       assert response.status_code == 200
   ```

### **Data Model Updates**

1. **Update Pydantic Models**
   ```python
   # app/models/new_feature.py
   from pydantic import BaseModel, Field
   
   class NewFeature(BaseModel):
       id: str = Field(..., description="Unique identifier")
       name: str = Field(..., description="Feature name")
       description: str = Field(default="", description="Feature description")
   ```

2. **Update Database Schema**
   ```python
   # app/storage/schemas.py
   NEW_FEATURE_SCHEMA = {
       "id": "varchar",
       "name": "varchar",
       "description": "text",
       "created_at": "timestamp",
       "updated_at": "timestamp",
       "deleted": "boolean",
       "deleted_at": "timestamp",
       "deleted_by": "varchar"
   }
   ```

3. **Update Storage Operations**
   ```python
   # app/storage/endpoints/new_feature/new_feature_storage.py
   async def create_new_feature(self, feature: NewFeature):
       # Implementation with schema validation
       pass
   ```

## 🚀 **Performance Optimization**

### **Database Optimization**

#### **Query Optimization**
- **Use Indexes**: Create indexes for frequently queried columns
- **Limit Results**: Use pagination and result limiting
- **Optimize Joins**: Minimize join complexity and use appropriate join types
- **Use Predicates**: Leverage VAST predicates for efficient filtering

#### **Connection Management**
- **Connection Pooling**: Reuse database connections
- **Connection Limits**: Set appropriate connection limits
- **Timeout Configuration**: Configure appropriate timeouts
- **Health Monitoring**: Monitor connection health and performance

### **Caching Strategy**

#### **Application Caching**
- **In-Memory Cache**: Fast access to frequently used data
- **TTL Management**: Automatic cache expiration
- **Cache Invalidation**: Smart cache invalidation strategies
- **Memory Management**: Monitor and control cache memory usage

#### **Storage Caching**
- **CDN Integration**: Use CDN for static content
- **Browser Caching**: Leverage HTTP caching headers
- **Storage Optimization**: Optimize storage access patterns

### **Async Operations**

#### **Non-Blocking Operations**
- **Async/Await**: Use async/await for I/O operations
- **Background Tasks**: Use FastAPI background tasks for long operations
- **Queue Management**: Implement job queues for heavy operations
- **Timeout Handling**: Proper timeout handling for async operations

## 🔍 **Monitoring and Observability**

### **Application Metrics**

#### **Business Metrics**
- **API Usage**: Request rates, response times, error rates
- **Storage Usage**: Data growth, storage efficiency
- **User Activity**: Active users, usage patterns
- **Performance**: Response times, throughput

#### **Technical Metrics**
- **System Resources**: CPU, memory, disk, network
- **Database Performance**: Query times, connection usage
- **Storage Performance**: I/O operations, latency
- **Cache Performance**: Hit rates, memory usage

### **Logging Strategy**

#### **Structured Logging**
```python
import logging
from app.core.tams_logging import get_logger

logger = get_logger(__name__)

logger.info("Operation completed", extra={
    "operation": "create_flow",
    "flow_id": flow_id,
    "duration_ms": duration_ms,
    "user_id": user_id
})
```

#### **Log Levels**
- **DEBUG**: Detailed debugging information
- **INFO**: General information about program execution
- **WARNING**: Warning messages for potentially problematic situations
- **ERROR**: Error messages for serious problems
- **CRITICAL**: Critical error messages that may prevent the program from running

### **Health Checks**

#### **Health Endpoints**
```python
@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "dependencies": {
            "database": await check_database_health(),
            "storage": await check_storage_health()
        }
    }
```

#### **Health Monitoring**
- **Endpoint Health**: Monitor all service endpoints
- **Dependency Health**: Monitor external dependencies
- **Performance Health**: Monitor performance metrics
- **Alert Generation**: Generate alerts for health issues

## 🔒 **Security Development**

### **Input Validation**

#### **Pydantic Validation**
```python
from pydantic import BaseModel, Field, validator

class FlowCreate(BaseModel):
    id: str = Field(..., min_length=1, max_length=255)
    source_id: str = Field(..., min_length=1, max_length=255)
    format: str = Field(..., regex=r"^urn:x-nmos:format:[a-z]+$")
    
    @validator('id')
    def validate_id(cls, v):
        if not v.isalnum() and '-' not in v:
            raise ValueError('ID must be alphanumeric with optional hyphens')
        return v
```

#### **SQL Injection Prevention**
- **Parameterized Queries**: Use parameterized queries for all database operations
- **Input Sanitization**: Validate and sanitize all input data
- **Escape Special Characters**: Properly escape special characters in queries
- **Use ORM**: Use ORM methods that automatically handle parameterization

### **Authentication and Authorization**

#### **JWT Implementation**
```python
from jose import JWTError, jwt
from datetime import datetime, timedelta

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
```

#### **Role-Based Access Control**
```python
from functools import wraps
from fastapi import HTTPException, Depends

def require_role(required_role: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            user_role = get_current_user_role()
            if user_role != required_role:
                raise HTTPException(status_code=403, detail="Insufficient permissions")
            return await func(*args, **kwargs)
        return wrapper
    return decorator
```

## 📦 **Deployment and DevOps**

### **Docker Configuration**

#### **Multi-Stage Builds**
```dockerfile
# Build stage
FROM python:3.12-slim as builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --user -r requirements.txt

# Runtime stage
FROM python:3.12-slim
WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY . .
CMD ["python", "run.py"]
```

#### **Environment Configuration**
```yaml
# docker-compose.yml
version: '3.8'
services:
  tams-api:
    build: .
    environment:
      - VAST_ENDPOINT=${VAST_ENDPOINT}
      - S3_ENDPOINT_URL=${S3_ENDPOINT_URL}
    ports:
      - "8000:8000"
```

### **Kubernetes Deployment**

#### **Deployment Configuration**
```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: tams-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: tams-api
  template:
    metadata:
      labels:
        app: tams-api
    spec:
      containers:
      - name: tams-api
        image: tams-api:latest
        ports:
        - containerPort: 8000
        env:
        - name: VAST_ENDPOINT
          valueFrom:
            configMapKeyRef:
              name: tams-config
              key: vast_endpoint
```

#### **Service Configuration**
```yaml
# k8s/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: tams-api-service
spec:
  selector:
    app: tams-api
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: LoadBalancer
```

### **CI/CD Pipeline**

#### **GitHub Actions**
```yaml
# .github/workflows/ci.yml
name: CI/CD Pipeline
on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.12'
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install -r requirements-dev.txt
    - name: Run tests
      run: |
        pytest tests/ --cov=app --cov-report=xml
    - name: Upload coverage
      uses: codecov/codecov-action@v3
```

## 📚 **Documentation Standards**

### **Code Documentation**

#### **Function Docstrings**
```python
def create_flow(flow_data: FlowCreate, storage: FlowStorage) -> Flow:
    """
    Create a new media flow.
    
    Args:
        flow_data: Flow creation data with validation
        storage: Flow storage interface for persistence
        
    Returns:
        Flow: Created flow object with generated ID
        
    Raises:
        ValidationError: If flow data is invalid
        StorageError: If storage operation fails
        DuplicateError: If flow ID already exists
        
    Example:
        >>> flow_data = FlowCreate(id="flow-1", source_id="source-1", format="video")
        >>> flow = create_flow(flow_data, storage)
        >>> print(flow.id)
        'flow-1'
    """
    # Implementation
    pass
```

#### **Class Documentation**
```python
class FlowStorage:
    """
    Storage interface for media flow operations.
    
    This class provides a clean interface for storing and retrieving
    media flow data from the underlying storage backend.
    
    Attributes:
        vast_core: VAST database core for metadata storage
        s3_core: S3 core for media segment storage
        
    Methods:
        create_flow: Create a new flow
        get_flow: Retrieve flow by ID
        update_flow: Update existing flow
        delete_flow: Delete flow (soft or hard delete)
        list_flows: List flows with filtering and pagination
    """
    
    def __init__(self, vast_core: VastCore, s3_core: S3Core):
        self.vast_core = vast_core
        self.s3_core = s3_core
```

### **API Documentation**

#### **OpenAPI Specifications**
```python
@router.post("/flows", response_model=Flow, status_code=201)
async def create_flow(
    flow: FlowCreate,
    storage: FlowStorage = Depends(get_flow_storage)
) -> Flow:
    """
    Create a new media flow.
    
    This endpoint creates a new media flow with the specified attributes.
    The flow will be associated with the provided source and can be used
    to store media segments.
    
    - **id**: Unique identifier for the flow
    - **source_id**: ID of the associated media source
    - **format**: Media format (video, audio, data, image, multi)
    - **codec**: Media codec specification
    - **frame_width**: Video frame width (for video flows)
    - **frame_height**: Video frame height (for video flows)
    - **frame_rate**: Video frame rate (for video flows)
    - **label**: Human-readable flow label
    - **description**: Detailed flow description
    - **tags**: Key-value metadata tags
    
    Returns:
        Flow: Created flow object with all attributes
        
    Raises:
        400: Bad Request - Invalid flow data
        409: Conflict - Flow ID already exists
        500: Internal Server Error - Storage operation failed
    """
    return await storage.create_flow(flow)
```

## 🚀 **Performance and Scalability**

### **Load Testing**

#### **Load Test Tools**
```bash
# Install load testing tools
pip install locust

# Run load tests
locust -f tests/load/locustfile.py --host=http://localhost:8000
```

#### **Performance Benchmarks**
```python
# tests/performance/test_performance.py
import asyncio
import time
from app.storage.endpoints.flows import FlowStorage

async def benchmark_flow_creation():
    storage = FlowStorage()
    start_time = time.time()
    
    for i in range(1000):
        flow_data = FlowCreate(id=f"flow-{i}", source_id="source-1", format="video")
        await storage.create_flow(flow_data)
    
    end_time = time.time()
    duration = end_time - start_time
    rate = 1000 / duration
    
    print(f"Created 1000 flows in {duration:.2f} seconds")
    print(f"Rate: {rate:.2f} flows/second")
```

### **Scaling Strategies**

#### **Horizontal Scaling**
- **Load Balancing**: Distribute requests across multiple instances
- **Stateless Design**: No server-side state dependencies
- **Database Sharding**: Horizontal database scaling
- **Storage Distribution**: Multi-region storage support

#### **Vertical Scaling**
- **Resource Optimization**: Optimize CPU and memory usage
- **Connection Pooling**: Efficient database connection management
- **Caching Layers**: Multi-level performance optimization
- **Query Optimization**: Database query performance tuning

## 🔮 **Future Development**

### **Planned Features**

#### **Real-Time Capabilities**
- **WebSocket Support**: Real-time event streaming
- **Event Sourcing**: Event-driven architecture
- **Stream Processing**: Real-time data processing
- **Live Analytics**: Real-time analytics dashboards

#### **Advanced Analytics**
- **Machine Learning**: AI-powered insights
- **Predictive Analytics**: Future trend prediction
- **Anomaly Detection**: Automatic issue detection
- **Performance Optimization**: AI-driven optimization

#### **Enhanced Security**
- **OAuth2 Integration**: Standard authentication
- **Role-Based Access**: Fine-grained permissions
- **Audit Logging**: Comprehensive audit trails
- **Encryption**: End-to-end encryption

### **Technology Evolution**

#### **Database Enhancements**
- **Advanced VAST Features**: New VAST capabilities
- **Graph Database**: Relationship modeling
- **Time-Series Optimization**: Enhanced time-series support
- **Distributed Queries**: Cross-cluster querying

#### **Storage Improvements**
- **Object Storage Optimization**: Enhanced S3 performance
- **CDN Integration**: Global content delivery
- **Compression Algorithms**: Advanced compression
- **Deduplication**: Storage deduplication

This development documentation provides comprehensive guidance for developing, testing, and maintaining the TAMS API system. It covers all aspects of the development lifecycle from initial setup to production deployment and future enhancements.
