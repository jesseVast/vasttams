# VAST TAMS (Time-addressable Media Store) API

A comprehensive FastAPI implementation of the BBC TAMS API specification with VAST Database and VAST S3 integration for high-performance time-series analytics and S3-compatible storage for media segments.

## 🚀 Features

- **Full TAMS API Compliance**: Implements the complete BBC TAMS API specification v6.0
- **VAST Database Integration**: High-performance columnar storage using vastdbmanager with Apache Arrow
- **S3-Compatible Storage**: Hybrid storage with metadata in VAST DB and media segments in S3
- **Time-Series Analytics**: Optimized for media flow segments with time ranges
- **RESTful API**: Complete CRUD operations for sources, flows, segments, and objects
- **Analytics Endpoints**: Built-in analytics for flow usage, storage patterns, and time analysis
- **Comprehensive Observability**: Prometheus metrics, OpenTelemetry tracing, and Grafana dashboards
- **Modular Architecture**: Clean separation of concerns with dedicated routers for each domain
- **Event-Driven Webhooks**: Complete webhook system with real-time event notifications for media operations
- **Automatic Object Management**: Objects are automatically created and updated when segments are created
- **Docker Support**: Containerized deployment with Docker and docker-compose
- **Kubernetes Ready**: Complete K8s manifests for production deployment
- **Comprehensive Testing**: Automated test suite for all endpoints
- **Pydantic v2 Compatible**: Modern data validation with RootModel support
- **Soft Delete Extension**: Vendor-specific enhancement with optional soft delete and cascade delete capabilities
- **Data Integrity**: Maintains referential integrity with cascade operations and automatic object tracking

## 🏗️ Architecture

<img width="822" height="430" alt="TAMS_Architecture-Live_white" src="https://github.com/user-attachments/assets/23ea1987-4b30-468f-89e4-a9a3778a2a02" />

The application uses a hybrid storage approach:
- **VAST Database**: Stores metadata (sources, flows, segments) with optimized schemas
- **S3-Compatible Storage**: Stores actual media segment data with presigned URLs
- **Time-Series Optimization**: Automatic time range parsing and indexing for efficient queries

## 📁 Project Structure

```
bbctams/
├── app/                    # Core application code
├── api/                    # API schemas and OpenAPI specs
├── tests/                  # Test suite
├── k8s/                    # Kubernetes manifests
├── observability/          # Observability stack config
├── docker/                 # Docker configuration
├── docs/                   # Documentation
└── mgmt/                   # Management scripts
```

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
   # Or use the development server
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

5. **Access the API**
   - API: http://localhost:8000
   - Interactive Documentation: http://localhost:8000/docs
   - ReDoc Documentation: http://localhost:8000/redoc
   - Health Check: http://localhost:8000/health
   - Metrics: http://localhost:8000/metrics

### Docker Deployment

```bash
docker-compose up --build
```

### Kubernetes Deployment

```bash
kubectl apply -k k8s/
```

## 📖 Documentation

- **[USAGE.md](USAGE.md)** - Detailed usage examples and API usage
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Architecture details and technical information
- **[API_REFERENCE.md](API_REFERENCE.md)** - Complete API endpoint documentation
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Deployment and configuration information
- **[OBSERVABILITY.md](OBSERVABILITY.md)** - Observability and monitoring setup
- **[SOFT_DELETE_EXTENSION.md](SOFT_DELETE_EXTENSION.md)** - Soft delete extension documentation

## 🔑 Key Concepts

### Media Segments and URLs

TAMS uses a segment-based approach where media content is divided into time-based segments. Each segment provides **two types of URLs** for different operations:

#### **GET URLs** - Data Retrieval
- **Purpose**: Download or stream the actual media content
- **Operation**: HTTP GET request
- **Response**: Binary media data (video, audio, etc.)
- **Use Case**: Media playback, content delivery, file downloads

#### **HEAD URLs** - Metadata Retrieval
- **Purpose**: Get metadata about the media segment without downloading content
- **Operation**: HTTP HEAD request
- **Response**: HTTP headers with metadata (file size, content type, etc.)
- **Use Case**: File information, size checking, content type verification

### Fetching Segment URLs

To get the URLs for a segment:

```bash
# Get all segments for a flow
curl "http://localhost:8000/flows/{flow_id}/segments"

# Response includes get_urls array with both URL types:
{
  "object_id": "segment-123",
  "timerange": "2025-08-23T14:00:00Z/2025-08-23T14:05:00Z",
  "get_urls": [
    {
      "url": "http://s3.example.com/...",
      "label": "GET access for segment segment-123"
    },
    {
      "url": "http://s3.example.com/...",
      "label": "HEAD access for segment segment-123"
    }
  ]
}
```

### Using the URLs

```bash
# Download media content (GET)
curl -O "$(curl -s 'http://localhost:8000/flows/{flow_id}/segments' | jq -r '.[0].get_urls[] | select(.label | contains("GET")) | .url')"

# Get metadata only (HEAD)
curl -I "$(curl -s 'http://localhost:8000/flows/{flow_id}/segments' | jq -r '.[0].get_urls[] | select(.label | contains("HEAD")) | .url')"
```

## 🧪 Testing

```bash
# Run all tests
python -m pytest

# Run specific test categories
python -m pytest tests/test_integration/
python -m pytest tests/test_storage/
python -m pytest tests/test_api/
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass (`python -m pytest`)
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

For issues and questions:
- 📖 Check the interactive documentation at `/docs`
- 🔍 Review the test examples in the `tests/` directory
- 🐛 Open an issue on GitHub with detailed information
- 💬 Join our community discussions

## 🚀 Roadmap

- [x] **Event-driven webhook system** - ✅ **COMPLETED**
- [x] **Automatic object management** - ✅ **COMPLETED**
- [x] **Dual URL support (GET/HEAD)** - ✅ **COMPLETED**
- [ ] Real-time event streaming with WebSockets
- [ ] Advanced analytics with machine learning
- [ ] Multi-region deployment support
- [ ] Enhanced security with OAuth2/JWT
- [ ] GraphQL API support
- [ ] Plugin system for custom storage backends
