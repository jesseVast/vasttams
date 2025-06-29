# TAMS (Time-addressable Media Store) API

A comprehensive FastAPI implementation of the BBC TAMS API specification with VAST database integration for high-performance time-series analytics and S3-compatible storage for media segments.

## 🚀 Features

- **Full TAMS API Compliance**: Implements the complete BBC TAMS API specification v6.0
- **VAST Database Integration**: High-performance columnar storage using vastdbmanager with Apache Arrow
- **S3-Compatible Storage**: Hybrid storage with metadata in VAST DB and media segments in S3
- **Time-Series Analytics**: Optimized for media flow segments with time ranges
- **RESTful API**: Complete CRUD operations for sources, flows, segments, and objects
- **Analytics Endpoints**: Built-in analytics for flow usage, storage patterns, and time analysis
- **Webhook Support**: Event-driven notifications for media operations
- **Docker Support**: Containerized deployment with Docker and docker-compose
- **Kubernetes Ready**: Complete K8s manifests for production deployment
- **Comprehensive Testing**: Automated test suite for all endpoints
- **Pydantic v2 Compatible**: Modern data validation with RootModel support

## 🏗️ Architecture

### Hybrid Storage Architecture
The application uses a hybrid storage approach:

- **VAST Database**: Stores metadata (sources, flows, segments) with optimized schemas
- **S3-Compatible Storage**: Stores actual media segment data with presigned URLs
- **Time-Series Optimization**: Automatic time range parsing and indexing for efficient queries

### VAST Database Store
The application uses the `vastdbmanager.py` module to provide a clean interface to VAST Database:

- **Columnar Storage**: Apache Arrow schemas with optimized table structures
- **Time-Series Optimization**: Automatic time range parsing and indexing
- **Transaction Support**: ACID-like operations with rollback capability
- **Schema Management**: Automatic table creation and schema discovery
- **Analytics Engine**: Built-in statistical analysis and aggregation
- **Connection Management**: Robust connection handling with retry logic

### S3 Store Integration
The `s3_store.py` module provides:

- **Media Segment Storage**: Efficient storage of large media files
- **Presigned URLs**: Secure, time-limited access to media segments
- **Hierarchical Organization**: Year/month/day based storage structure
- **Metadata Tracking**: Comprehensive metadata for each segment
- **Multi-format Support**: Handles bytes, file paths, and file-like objects

### Database Schema
The VAST store creates the following tables with optimized schemas:

- **sources**: Media sources with metadata and collections
- **flows**: Media flows with format-specific attributes (video, audio, data, image, multi)
- **segments**: Time-series optimized flow segments with time ranges
- **objects**: Media objects with access tracking
- **webhooks**: Event notification configuration
- **deletion_requests**: Media deletion tracking

## 📋 API Endpoints

### Core TAMS Endpoints
- `GET /` - Service information and available paths
- `GET /health` - Health check endpoint
- `GET /openapi.json` - OpenAPI specification (JSON)
- `GET /service` - Service configuration and capabilities
- `POST /service` - Update service configuration

### Sources Management
- `GET /sources` - List sources with filtering and pagination
- `POST /sources` - Create new source
- `GET /sources/{id}` - Get source by ID
- `PUT /sources/{id}` - Update source
- `DELETE /sources/{id}` - Delete source
- `GET /sources/{id}/tags` - Get source tags
- `PUT /sources/{id}/tags/{name}` - Update source tag
- `DELETE /sources/{id}/tags/{name}` - Delete source tag
- `GET /sources/{id}/description` - Get source description
- `PUT /sources/{id}/description` - Update source description
- `GET /sources/{id}/label` - Get source label
- `PUT /sources/{id}/label` - Update source label

### Flows Management
- `GET /flows` - List flows with filtering and pagination
- `POST /flows` - Create new flow
- `GET /flows/{id}` - Get flow by ID
- `PUT /flows/{id}` - Update flow
- `DELETE /flows/{id}` - Delete flow
- `GET /flows/{id}/tags` - Get flow tags
- `PUT /flows/{id}/tags/{name}` - Update flow tag
- `DELETE /flows/{id}/tags/{name}` - Delete flow tag
- `GET /flows/{id}/description` - Get flow description
- `PUT /flows/{id}/description` - Update flow description
- `GET /flows/{id}/label` - Get flow label
- `PUT /flows/{id}/label` - Update flow label
- `GET /flows/{id}/read_only` - Get flow read-only status
- `PUT /flows/{id}/read_only` - Update flow read-only status
- `GET /flows/{id}/flow_collection` - Get flow collection (MultiFlow)
- `PUT /flows/{id}/flow_collection` - Update flow collection
- `DELETE /flows/{id}/flow_collection` - Delete flow collection

### Flow Segments
- `GET /flows/{id}/segments` - Get flow segments with time range filtering
- `POST /flows/{id}/segments` - Create flow segment (upload media data)
- `DELETE /flows/{id}/segments` - Delete flow segments
- `POST /flows/{id}/storage` - Allocate storage for flow segments

### Media Objects
- `GET /objects/{id}` - Get media object
- `POST /objects` - Create media object

### Analytics Endpoints
- `GET /analytics/flow-usage` - Flow usage statistics and format distribution
- `GET /analytics/storage-usage` - Storage usage analysis and access patterns
- `GET /analytics/time-range-analysis` - Time range patterns and duration analysis

### Management Endpoints
- `GET /service/webhooks` - List webhooks
- `POST /service/webhooks` - Create webhook
- `GET /flow-delete-requests` - List deletion requests
- `POST /flow-delete-requests` - Create deletion request
- `GET /flow-delete-requests/{id}` - Get deletion request by ID

## 🚀 Quick Start

### Prerequisites
- Python 3.12+
- VAST Database server (optional, can use mock for development)
- S3-compatible storage (MinIO, AWS S3, etc.)
- Docker (optional)

### Local Development

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd bbctams
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment**
   ```bash
   cp env.example .env
   # Edit .env with your VAST database and S3 configuration
   ```

4. **Run the application**
   ```bash
   python run.py
   ```

5. **Access the API**
   - API: http://localhost:8000
   - Interactive Documentation: http://localhost:8000/docs
   - ReDoc Documentation: http://localhost:8000/redoc
   - Health Check: http://localhost:8000/health

### Docker Deployment

1. **Build and run with docker-compose**
   ```bash
   docker-compose up --build
   ```

2. **Or build manually**
   ```bash
   docker build -t tams-api .
   docker run -p 8000:8000 tams-api
   ```

### Kubernetes Deployment

1. **Apply Kubernetes manifests**
   ```bash
   kubectl apply -k k8s/
   ```

2. **Check deployment status**
   ```bash
   kubectl get pods -n tams
   kubectl get services -n tams
   ```

## ⚙️ Configuration

### Environment Variables

Key configuration options in `.env`:

```env
# Server settings
HOST=0.0.0.0
PORT=8000
DEBUG=false

# VAST Database settings
VAST_ENDPOINT=http://main.vast.acme.com
VAST_ACCESS_KEY=test-access-key
VAST_SECRET_KEY=test-secret-key
VAST_BUCKET=tams-bucket
VAST_SCHEMA=tams-schema

# S3 Storage settings
S3_ENDPOINT_URL=http://s3.vast.acme.com
S3_ACCESS_KEY_ID=vast-s3-access-key
S3_SECRET_ACCESS_KEY=vast-s3-secret-key
S3_BUCKET_NAME=tams-bucket
S3_USE_SSL=false

# Logging
LOG_LEVEL=INFO

# Security
SECRET_KEY=your-secret-key-here-change-in-production
```

### VAST Database Configuration

The application uses the following VAST database settings:

```env
# VAST Database settings
VAST_ENDPOINT=http://main.vast.acme.com/
VAST_ACCESS_KEY=test-access-key
VAST_SECRET_KEY=test-secret-key
VAST_BUCKET=tams-bucket
VAST_SCHEMA=tams-schema
```

## 📖 API Usage Examples

### Create a Video Source
```bash
curl -X POST "http://localhost:8000/sources" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "format": "urn:x-nmos:format:video",
    "label": "Main Camera Feed",
    "description": "Primary camera source for live broadcast",
    "tags": {
      "location": "studio-a",
      "quality": "hd"
    }
  }'
```

### Create a Video Flow
```bash
curl -X POST "http://localhost:8000/flows" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "550e8400-e29b-41d4-a716-446655440001",
    "source_id": "550e8400-e29b-41d4-a716-446655440000",
    "format": "urn:x-nmos:format:video",
    "codec": "video/mp4",
    "frame_width": 1920,
    "frame_height": 1080,
    "frame_rate": "25/1",
    "label": "HD Video Stream"
  }'
```

### Upload Flow Segment
```bash
curl -X POST "http://localhost:8000/flows/550e8400-e29b-41d4-a716-446655440001/segments" \
  -H "Content-Type: multipart/form-data" \
  -F "segment={\"object_id\":\"seg_001\",\"timerange\":\"[0:0_10:0)\",\"sample_offset\":0,\"sample_count\":250}" \
  -F "file=@video_segment.mp4"
```

### Get Analytics
```bash
# Flow usage analytics
curl "http://localhost:8000/analytics/flow-usage"

# Storage usage analytics
curl "http://localhost:8000/analytics/storage-usage"

# Time range analysis
curl "http://localhost:8000/analytics/time-range-analysis"
```

### Create Webhook
```bash
curl -X POST "http://localhost:8000/service/webhooks" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://webhook.example.com/events",
    "api_key_name": "X-API-Key",
    "api_key_value": "your-webhook-secret",
    "events": ["source.created", "flow.updated", "segment.uploaded"]
  }'
```

## 🧪 Testing

### Run the test suite
```bash
# Basic API tests
python -m pytest tests/test_basic.py -v

# VAST store tests
python -m pytest tests/test_vast_store.py -v

# S3 store tests
python -m pytest tests/test_s3_store.py -v
```

### Test VAST Store directly
```bash
python tests/test_vast_store.py
```

The tests cover:
- Health check endpoint
- Service information
- Source creation and retrieval
- Flow creation and retrieval
- Flow segment upload and retrieval
- Analytics endpoints
- Webhook management
- VAST database operations
- S3 storage operations

## 🔧 Development

### Project Structure
```
bbctams/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application with all endpoints
│   ├── models.py            # Pydantic v2 models with RootModel support
│   ├── config.py            # Configuration management
│   ├── vast_store.py        # VAST store implementation
│   ├── vastdbmanager.py     # VAST database manager
│   ├── s3_store.py          # S3-compatible storage manager
│   └── utils.py             # Utility functions
├── api/
│   ├── openapi.json         # OpenAPI specification (auto-generated)
│   └── schemas/             # JSON schemas for validation
├── k8s/                     # Kubernetes manifests
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── ingress.yaml
│   ├── configmap.yaml
│   └── secrets.yaml
├── tests/
│   ├── test_basic.py        # Basic API tests
│   ├── test_vast_store.py   # VAST store tests
│   └── test_s3_store.py     # S3 store tests
├── docker-compose.yml       # Docker Compose configuration
├── Dockerfile              # Docker image definition
├── generate_openapi.py     # OpenAPI specification generator
├── requirements.txt        # Python dependencies
├── run.py                 # Application entry point
└── README.md              # This file
```

### OpenAPI Specification

The application includes a comprehensive OpenAPI specification that can be accessed at:

- **OpenAPI JSON**: `GET /openapi.json` - Raw OpenAPI specification
- **Interactive Docs**: `GET /docs` - Swagger UI documentation
- **ReDoc Docs**: `GET /redoc` - ReDoc documentation

#### Generating OpenAPI Specification

To regenerate the OpenAPI specification:

```bash
# Generate from the running application
python generate_openapi.py

# Or access directly via API
curl http://localhost:8000/openapi.json > api/openapi.json
```

The OpenAPI specification includes:
- All API endpoints with detailed descriptions
- Request/response schemas
- Query parameters and path variables
- Example requests and responses
- Error codes and descriptions
- Authentication requirements
- Tags for endpoint organization

### VAST Database Features

#### Columnar Storage
- Apache Arrow schemas for type safety
- Optimized table structures for TAMS data types
- Vectorized operations for analytics

#### Transaction Support
The vastdbmanager provides transaction support:
```python
with vast_store.db_manager.session.transaction() as tx:
    bucket = tx.bucket("tams-bucket")
    schema = bucket.schema("tams-schema")
    table = schema.table("sources")
    # Perform operations within transaction
```

#### Analytics Integration
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

#### Schema Management
Automatic table creation and schema discovery:
```python
# List all tables
tables = store.list_tables()

# List all schemas
schemas = store.list_schemas()

# Get table statistics
stats = store.get_table_stats("sources")
```

### S3 Store Features

#### Media Segment Storage
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

### Adding New Features

1. **New Data Types**: Add to `models.py` and update VAST store schemas
2. **New Endpoints**: Add to `main.py` with proper error handling
3. **New Analytics**: Extend `analytics_query` method in `vast_store.py`
4. **New Storage**: Extend `s3_store.py` for additional storage backends
5. **New Tests**: Add to test files or create new test files

## 🔒 Security

- **Input Validation**: All inputs validated with Pydantic v2 models
- **Authentication**: API key support for webhooks
- **Authorization**: Role-based access control (configurable)
- **HTTPS**: TLS/SSL support for production deployments
- **Rate Limiting**: Configurable rate limiting for API endpoints
- **CORS**: Configurable Cross-Origin Resource Sharing

## 📊 Monitoring

- **Health Checks**: Built-in health check endpoint
- **Logging**: Comprehensive logging with configurable levels
- **Metrics**: Built-in analytics and usage statistics
- **Error Tracking**: Detailed error responses and logging
- **Performance**: VAST database performance monitoring

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass (`python -m pytest`)
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

### Development Guidelines

- Follow PEP 8 style guidelines
- Add type hints to all functions
- Write comprehensive docstrings
- Add tests for all new functionality
- Update documentation for API changes
- Use conventional commit messages

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

For issues and questions:

- 📖 Check the interactive documentation at `/docs`
- 🔍 Review the test examples in the `tests/` directory
- 🐛 Open an issue on GitHub with detailed information
- 💬 Join our community discussions

### Common Issues

#### Pydantic v2 Compatibility
If you encounter Pydantic v2 errors, ensure you're using the updated models:
```python
# Old v1 syntax (deprecated)
tags = Tags(__root__={"key": "value"})

# New v2 syntax
tags = Tags({"key": "value"})
```

#### VAST Database Connection
If VAST database connection fails:
1. Check VAST server is running
2. Verify endpoint URL and credentials
3. Ensure network connectivity
4. Check firewall settings

#### S3 Storage Issues
If S3 storage operations fail:
1. Verify S3 endpoint is accessible
2. Check access key and secret
3. Ensure bucket exists and is writable
4. Verify SSL/TLS configuration

## 🚀 Roadmap

- [ ] Real-time event streaming with WebSockets
- [ ] Advanced analytics with machine learning
- [ ] Multi-region deployment support
- [ ] Enhanced security with OAuth2/JWT
- [ ] GraphQL API support
- [ ] Plugin system for custom storage backends
- [ ] Performance optimization for large-scale deployments
- [ ] Integration with popular media processing tools
