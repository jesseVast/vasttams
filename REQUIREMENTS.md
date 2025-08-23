# TAMS Project Requirements

This document outlines the requirements and dependencies for the TAMS (Time-addressable Media Store) API project.

## 🐍 Python Requirements

### Core Python Version
- **Python**: 3.12+ (required)
- **Python 3.11**: Not supported
- **Python 3.10**: Not supported
- **Python 3.9**: Not supported

### Why Python 3.12+?
- **Performance**: Significant performance improvements in Python 3.12
- **Type System**: Enhanced type system features
- **Error Messages**: Better error messages and debugging
- **Security**: Latest security updates and patches
- **Library Support**: Modern library compatibility

## 📦 Core Dependencies

### Web Framework
```
fastapi==0.115.14          # Modern, fast web framework
uvicorn[standard]==0.34.3  # ASGI server with standard extras
starlette==0.45.2          # ASGI toolkit (FastAPI dependency)
python-multipart==0.0.20   # Multipart form data handling
```

### Data Validation & Settings
```
pydantic==2.11.7           # Data validation using Python type annotations
pydantic-settings==2.10.1  # Settings management using Pydantic
```

### Authentication & Security
```
bcrypt==4.1.2              # Password hashing
PyJWT==2.8.0               # JSON Web Token implementation
python-jose[cryptography]==3.3.0  # JWT implementation with crypto
passlib[bcrypt]==1.7.4     # Password hashing library
```

### Environment & Configuration
```
python-dotenv==1.1.1       # Environment variable loading
click==8.1.7               # Command line interface creation
```

### Database & ORM
```
alembic==1.16.2            # Database migration tool
psycopg2-binary==2.9.9     # PostgreSQL adapter (binary)
```

### Caching & HTTP
```
redis==5.0.1               # Redis client library
httpx==0.28.1              # HTTP client library
```

### Testing
```
pytest==7.4.3              # Testing framework
pytest-asyncio==0.21.1     # Async testing support
pytest-cov==4.1.0          # Coverage reporting
```

## 🗄️ VAST Database Dependencies

### Core VAST Integration
```
vastdb==1.3.10             # VAST database Python client
ibis==3.3.0                # Data analysis framework
pyarrow==16.1.0            # Apache Arrow Python bindings
pandas==2.3.0              # Data manipulation and analysis
duckdb>=0.9.0              # In-process SQL database
```

### Why These Versions?
- **vastdb 1.3.10**: Latest stable version with full VAST API support
- **ibis 3.3.0**: Modern version with enhanced VAST integration
- **pyarrow 16.1.0**: Latest Arrow version for optimal performance
- **pandas 2.3.0**: Compatible with Python 3.12 and PyArrow 16
- **duckdb 0.9.0+**: Required for hybrid analytics (VAST + DuckDB)

## ☁️ S3 Storage Dependencies

### AWS/S3 Integration
```
boto3==1.34.135            # AWS SDK for Python
botocore==1.34.162         # Low-level AWS service access
```

### Version Compatibility Note
**Important**: boto3 1.34.135 is specifically required for compatibility with MinIO and other S3-compatible storage backends. Newer versions may add headers that cause compatibility issues.

## 🛠️ Utility Dependencies

### Date & Time
```
python-dateutil==2.9.0.post0  # Date utilities
pytz==2025.2                   # Timezone support
```

### General Utilities
```
deprecated==1.2.14             # Deprecation warnings
six==1.17.0                    # Python 2/3 compatibility
```

## 📊 Observability Dependencies

### Prometheus Integration
```
prometheus-client==0.22.1      # Prometheus metrics client
```

### OpenTelemetry Integration
```
opentelemetry-api==1.35.0      # OpenTelemetry API
opentelemetry-sdk==1.35.0      # OpenTelemetry SDK
opentelemetry-instrumentation-fastapi==0.56b0  # FastAPI instrumentation
opentelemetry-instrumentation-httpx==0.56b0    # HTTPX instrumentation
opentelemetry-instrumentation-logging==0.56b0  # Logging instrumentation
opentelemetry-exporter-prometheus==0.56b0      # Prometheus exporter
opentelemetry-exporter-jaeger==1.21.0          # Jaeger exporter
opentelemetry-exporter-otlp-proto-http==1.15.0 # OTLP HTTP exporter
```

### System Monitoring
```
psutil==7.0.0                  # System and process utilities
```

## 🔧 Development Dependencies

### Development Tools
```
# Install with: pip install -r requirements-dev.txt
pytest==7.4.3                  # Testing framework
pytest-asyncio==0.21.1         # Async testing support
pytest-cov==4.1.0              # Coverage reporting
black==23.12.0                 # Code formatter
flake8==6.1.0                  # Linter
mypy==1.8.0                    # Type checker
pre-commit==3.6.0              # Git hooks
```

### Code Quality
```
# Code formatting and linting
black==23.12.0                 # Uncompromising code formatter
flake8==6.1.0                  # Style guide enforcement
mypy==1.8.0                    # Static type checking
isort==5.13.2                  # Import sorting
```

### Documentation
```
# Documentation generation
mkdocs==1.5.3                  # Static site generator
mkdocs-material==9.4.8         # Material theme for MkDocs
mkdocstrings[python]==0.24.0   # Python docstring processing
```

## 🐳 Container Dependencies

### Docker Requirements
- **Docker**: 20.10+ (required)
- **Docker Compose**: 2.0+ (required)
- **BuildKit**: Enabled (recommended)

### Base Images
```dockerfile
# Build stage
FROM python:3.12-slim as builder

# Runtime stage
FROM python:3.12-slim
```

## ☸️ Kubernetes Dependencies

### Kubernetes Requirements
- **Kubernetes**: 1.24+ (required)
- **kubectl**: 1.24+ (required)
- **Helm**: 3.12+ (optional, for advanced deployments)

### Supported Kubernetes Versions
- **1.24**: Minimum supported version
- **1.25**: Recommended minimum
- **1.26**: Recommended
- **1.27**: Recommended
- **1.28**: Latest stable

## 🖥️ System Requirements

### Operating Systems
- **Linux**: Ubuntu 20.04+, CentOS 8+, RHEL 8+
- **macOS**: 12.0+ (Monterey)
- **Windows**: 10+ (with WSL2 recommended)

### Hardware Requirements
- **CPU**: 2+ cores (4+ recommended)
- **Memory**: 4GB+ RAM (8GB+ recommended)
- **Storage**: 10GB+ free space (50GB+ recommended)
- **Network**: Stable internet connection for dependencies

### Network Requirements
- **Ports**: 8000 (API), 9090 (VAST/S3), 3000 (Grafana), 9090 (Prometheus)
- **Firewall**: Configured to allow required ports
- **DNS**: Proper DNS resolution for external services

## 🔒 Security Requirements

### Authentication
- **API Keys**: Required for production deployments
- **JWT Tokens**: Supported for advanced authentication
- **OAuth2**: Planned for future releases

### Encryption
- **TLS/SSL**: Required for production (HTTPS)
- **Data at Rest**: VAST database encryption
- **Data in Transit**: TLS 1.3 recommended

### Access Control
- **Role-Based Access**: Planned for future releases
- **IP Whitelisting**: Supported via firewall rules
- **Rate Limiting**: Built-in rate limiting support

## 📊 Performance Requirements

### Response Times
- **API Endpoints**: < 100ms for simple operations
- **Database Queries**: < 500ms for complex queries
- **File Uploads**: < 1s per MB for S3 operations

### Throughput
- **Concurrent Users**: 100+ simultaneous users
- **Request Rate**: 1000+ requests per second
- **Data Ingestion**: 100MB+ per second

### Scalability
- **Horizontal Scaling**: Supported via Kubernetes
- **Load Balancing**: Built-in load balancing
- **Auto-scaling**: Kubernetes HPA support

## 🧪 Testing Requirements

### Test Coverage
- **Unit Tests**: > 90% coverage required
- **Integration Tests**: > 80% coverage required
- **API Tests**: > 95% coverage required

### Test Environments
- **Local Development**: Python virtual environment
- **CI/CD**: GitHub Actions with multiple Python versions
- **Staging**: Docker containers with real dependencies

### Test Data
- **Sample Data**: Provided test datasets
- **Mock Services**: Mock VAST and S3 services
- **Performance Tests**: Load testing scenarios

## 📚 Documentation Requirements

### Required Documentation
- **API Documentation**: OpenAPI/Swagger specification
- **Architecture**: System architecture documentation
- **Deployment**: Deployment and configuration guides
- **Development**: Development and contribution guidelines

### Documentation Standards
- **Markdown**: All documentation in Markdown format
- **Code Examples**: Working code examples for all features
- **Diagrams**: Architecture and flow diagrams
- **Versioning**: Documentation versioned with code

## 🚀 Deployment Requirements

### Production Deployment
- **Environment**: Production-ready configuration
- **Monitoring**: Prometheus + Grafana monitoring
- **Logging**: Structured logging with log aggregation
- **Backup**: Automated backup procedures

### Development Deployment
- **Local Development**: Docker Compose setup
- **Hot Reload**: Development server with auto-reload
- **Debug Mode**: Comprehensive debugging tools
- **Testing**: Local testing environment

## 🔄 Maintenance Requirements

### Updates & Patches
- **Security Updates**: Monthly security patch reviews
- **Dependency Updates**: Quarterly dependency updates
- **Version Compatibility**: Maintain Python 3.12+ compatibility

### Monitoring & Alerting
- **Health Checks**: Automated health monitoring
- **Performance Monitoring**: Real-time performance tracking
- **Error Alerting**: Automated error notification
- **Capacity Planning**: Resource usage monitoring

## 📋 Compliance Requirements

### Data Protection
- **GDPR**: Basic GDPR compliance features
- **Data Retention**: Configurable data retention policies
- **Data Export**: Data export capabilities
- **Privacy**: Privacy-focused design

### Industry Standards
- **TAMS API**: Full TAMS API 7.0 compliance
- **REST Standards**: RESTful API design principles
- **OpenAPI**: OpenAPI 3.0 specification compliance
- **HTTP Standards**: HTTP/1.1 and HTTP/2 support

## 🎯 Future Requirements

### Planned Features
- **GraphQL API**: Alternative query interface
- **Real-time Streaming**: WebSocket support
- **Machine Learning**: AI-powered analytics
- **Edge Computing**: Distributed processing

### Technology Evolution
- **Python 3.13+**: Future Python version support
- **Advanced VAST**: New VAST database features
- **Cloud Native**: Enhanced cloud platform support
- **Microservices**: Service mesh architecture

## 📝 Installation Instructions

### Quick Start
```bash
# Clone repository
git clone <repository-url>
cd bbctams

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install development dependencies (optional)
pip install -r requirements-dev.txt
```

### Docker Installation
```bash
# Build and run with Docker
cd docker
docker-compose up --build
```

### Kubernetes Installation
```bash
# Apply Kubernetes manifests
kubectl apply -k k8s/
```

## 🔍 Verification

### Verify Installation
```bash
# Check Python version
python --version  # Should be 3.12+

# Check dependencies
pip list

# Run tests
pytest tests/

# Start application
python run.py
```

### Health Checks
```bash
# API health
curl http://localhost:8000/health

# Metrics endpoint
curl http://localhost:8000/metrics

# OpenAPI spec
curl http://localhost:8000/openapi.json
```

## 🆘 Support

### Getting Help
- **Documentation**: Comprehensive documentation provided
- **GitHub Issues**: Bug reports and feature requests
- **Community**: Community discussions and support
- **Examples**: Working code examples for all features

### Troubleshooting
- **Common Issues**: Documented common problems and solutions
- **Debug Mode**: Built-in debugging capabilities
- **Logs**: Comprehensive logging for troubleshooting
- **Diagnostics**: Built-in diagnostic tools

This requirements document provides comprehensive information about the TAMS project dependencies, system requirements, and deployment considerations. For the most up-to-date information, always refer to the current requirements.txt files and project documentation.
