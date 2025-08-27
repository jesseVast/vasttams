# TAMS Deployment Guide

This document provides comprehensive information about deploying and configuring the TAMS API, including environment setup, Docker deployment, Kubernetes deployment, and observability configuration.

## 📖 Table of Contents

- [Prerequisites](#prerequisites)
- [Environment Configuration](#environment-configuration)
- [Local Development](#local-development)
- [Docker Deployment](#docker-deployment)
- [Kubernetes Deployment](#kubernetes-deployment)
- [Observability Stack](#observability-stack)
- [Production Considerations](#production-considerations)
- [Troubleshooting](#troubleshooting)

## 🔧 Prerequisites

### System Requirements

- **Python**: 3.12+
- **Memory**: Minimum 2GB RAM, recommended 4GB+
- **Storage**: Minimum 10GB free space
- **Network**: Access to VAST database and S3 storage endpoints

### Required Services

- **VAST Database**: Running and accessible
- **S3-Compatible Storage**: MinIO, AWS S3, or similar
- **Docker** (optional): For containerized deployment
- **Kubernetes** (optional): For K8s deployment

### Development Tools

- **Git**: For source code management
- **Python pip**: For dependency management
- **curl** or **Postman**: For API testing
- **jq**: For JSON processing (optional but recommended)

## ⚙️ Environment Configuration

### Environment Variables

The application uses environment variables for configuration. Copy the example file and customize it:

```bash
cp env.example .env
```

#### Server Settings

```env
# Server configuration
HOST=0.0.0.0
PORT=8000
DEBUG=false
LOG_LEVEL=INFO

# Security
SECRET_KEY=your-secret-key-here-change-in-production
```

#### VAST Database Settings

```env
# VAST Database configuration
VAST_ENDPOINT=http://main.vast.acme.com
VAST_ACCESS_KEY=test-access-key
VAST_SECRET_KEY=test-secret-key
VAST_BUCKET=tams-bucket
VAST_SCHEMA=tams-schema
```

#### S3 Storage Settings

```env
# S3 Storage configuration
S3_ENDPOINT_URL=http://s3.vast.acme.com
S3_ACCESS_KEY_ID=vast-s3-access-key
S3_SECRET_ACCESS_KEY=vast-s3-secret-key
S3_BUCKET_NAME=tams-bucket
S3_USE_SSL=false
```

#### Advanced Configuration

```env
# Connection settings
VAST_CONNECTION_TIMEOUT=30
VAST_READ_TIMEOUT=60
S3_CONNECTION_TIMEOUT=30
S3_READ_TIMEOUT=60

# URL generation settings
S3_PRESIGNED_URL_EXPIRY=3600
S3_MAX_RETRIES=3

# Logging and monitoring
TELEMETRY_ENABLED=true
METRICS_ENABLED=true
TRACING_ENABLED=true
```

### Configuration Validation

The application validates configuration on startup:

```bash
# Check configuration
python -c "from app.config import get_settings; print('Configuration valid')"
```

## 🚀 Local Development

### Installation

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
   ```

4. **Set up environment**
   ```bash
   cp env.example .env
   # Edit .env with your configuration
   ```

### Running the Application

#### Development Server

```bash
# Start with auto-reload
python run.py

# Or use uvicorn directly
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Production Server

```bash
# Start production server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Access Points

- **API**: http://localhost:8000
- **Interactive Documentation**: http://localhost:8000/docs
- **ReDoc Documentation**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health
- **Metrics**: http://localhost:8000/metrics

## 🐳 Docker Deployment

### Quick Start

```bash
# Build and run with docker-compose
docker-compose up --build

# Run in background
docker-compose up -d --build
```

### Docker Compose Configuration

The `docker-compose.yml` file includes:

- **TAMS API**: Main application container
- **VAST Database**: Database service (optional)
- **MinIO**: S3-compatible storage (optional)
- **Network**: Internal network for services

#### Custom Configuration

```yaml
version: '3.8'
services:
  tams-api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - VAST_ENDPOINT=http://vast:8080
      - S3_ENDPOINT_URL=http://minio:9000
    depends_on:
      - vast
      - minio
    networks:
      - tams-network

  vast:
    image: vastdb/vast:latest
    ports:
      - "8080:8080"
    environment:
      - VAST_ACCESS_KEY=test-access-key
      - VAST_SECRET_KEY=test-secret-key
    networks:
      - tams-network

  minio:
    image: minio/minio:latest
    ports:
      - "9000:9000"
      - "9001:9001"
    environment:
      - MINIO_ROOT_USER=minioadmin
      - MINIO_ROOT_PASSWORD=minioadmin
    command: server /data --console-address ":9001"
    networks:
      - tams-network

networks:
  tams-network:
    driver: bridge
```

### Manual Docker Build

```bash
# Build image
docker build -t tams-api .

# Run container
docker run -p 8000:8000 \
  -e VAST_ENDPOINT=http://your-vast-endpoint \
  -e S3_ENDPOINT_URL=http://your-s3-endpoint \
  tams-api
```

### Docker Environment Variables

You can override environment variables when running containers:

```bash
docker run -p 8000:8000 \
  -e VAST_ENDPOINT=http://vast.example.com \
  -e VAST_ACCESS_KEY=your-key \
  -e VAST_SECRET_KEY=your-secret \
  -e S3_ENDPOINT_URL=http://s3.example.com \
  -e S3_ACCESS_KEY_ID=your-s3-key \
  -e S3_SECRET_ACCESS_KEY=your-s3-secret \
  tams-api
```

## ☸️ Kubernetes Deployment

### Quick Deployment

```bash
# Apply all Kubernetes manifests
kubectl apply -k k8s/

# Check deployment status
kubectl get pods -n tams
kubectl get services -n tams
```

### Namespace Setup

```bash
# Create namespace
kubectl create namespace tams

# Set namespace as default
kubectl config set-context --current --namespace=tams
```

### Individual Components

#### ConfigMap

```bash
# Apply configuration
kubectl apply -f k8s/configmap.yaml

# View configuration
kubectl get configmap tams-config -o yaml
```

#### Secrets

```bash
# Create secrets (replace with your values)
kubectl create secret generic tams-secrets \
  --from-literal=vast-access-key=your-key \
  --from-literal=vast-secret-key=your-secret \
  --from-literal=s3-access-key-id=your-s3-key \
  --from-literal=s3-secret-access-key=your-s3-secret

# Or apply from file
kubectl apply -f k8s/secrets.yaml
```

#### Deployment

```bash
# Deploy application
kubectl apply -f k8s/deployment.yaml

# Check deployment status
kubectl get deployments
kubectl describe deployment tams-api
```

#### Service

```bash
# Create service
kubectl apply -f k8s/service.yaml

# Check service
kubectl get services
kubectl describe service tams-service
```

#### Ingress

```bash
# Apply ingress configuration
kubectl apply -f k8s/ingress.yaml

# Check ingress
kubectl get ingress
kubectl describe ingress tams-ingress
```

### Helm Deployment

The project includes Helm charts for advanced deployment:

```bash
# Install with Helm
helm install tams ./k8s/helm/

# Upgrade deployment
helm upgrade tams ./k8s/helm/

# Uninstall
helm uninstall tams
```

### Scaling

#### Horizontal Pod Autoscaler

```bash
# Apply HPA
kubectl apply -f k8s/hpa.yaml

# Check HPA status
kubectl get hpa
kubectl describe hpa tams-hpa
```

#### Manual Scaling

```bash
# Scale deployment
kubectl scale deployment tams-api --replicas=5

# Check replica count
kubectl get deployment tams-api
```

## 📊 Observability Stack

### Quick Start

```bash
# Start observability stack
./start-observability.sh

# Or use docker-compose
docker-compose -f docker-compose.observability.yml up -d
```

### Components

#### Prometheus

- **Configuration**: `observability/prometheus/prometheus.yml`
- **Access**: http://localhost:9090
- **Metrics**: TAMS API metrics collection

#### Grafana

- **Configuration**: `observability/grafana/`
- **Access**: http://localhost:3000 (admin/admin)
- **Dashboards**: Pre-configured TAMS dashboards

#### Alertmanager

- **Configuration**: `observability/alertmanager/alertmanager.yml`
- **Access**: http://localhost:9093
- **Alerts**: Configurable alerting rules

### Metrics

The TAMS API exposes comprehensive metrics:

#### HTTP Metrics
- Request count and duration
- Status code distribution
- Endpoint usage patterns

#### Business Metrics
- Sources, flows, and segments count
- Storage usage and access patterns
- Object reuse statistics

#### System Metrics
- Memory and CPU usage
- Database connection status
- S3 operation performance

### Dashboards

Pre-configured Grafana dashboards include:

- **TAMS Overview**: High-level system status
- **API Performance**: Request metrics and response times
- **Storage Analytics**: S3 and database performance
- **Business Metrics**: Media content statistics

### Alerting

Configure alerts for:

- **High Error Rates**: 5xx responses > 5%
- **Slow Response Times**: P95 > 2 seconds
- **Storage Issues**: S3 operation failures
- **Database Issues**: Connection failures

## 🏭 Production Considerations

### Security

#### Network Security
- Use HTTPS/TLS in production
- Configure firewall rules
- Implement network policies
- Use VPN for internal access

#### Authentication & Authorization
- Implement OAuth2/JWT
- Add role-based access control
- Use API key management
- Implement rate limiting

#### Data Security
- Encrypt data at rest
- Use secure S3 endpoints
- Implement audit logging
- Regular security updates

### Performance

#### Scaling
- Horizontal scaling with load balancers
- Database connection pooling
- S3 operation optimization
- CDN integration for media content

#### Monitoring
- Real-time performance monitoring
- Automated alerting
- Performance baselining
- Capacity planning

#### Caching
- Redis for metadata caching
- CDN for media content
- Browser caching headers
- Response compression

### Reliability

#### High Availability
- Multi-zone deployment
- Database replication
- S3 cross-region replication
- Automated failover

#### Backup & Recovery
- Automated backups
- Point-in-time recovery
- Disaster recovery plan
- Regular testing

#### Maintenance
- Rolling updates
- Zero-downtime deployments
- Health check monitoring
- Automated rollbacks

## 🔧 Troubleshooting

### Common Issues

#### Connection Issues

**VAST Database Connection Failed**
```bash
# Check connectivity
curl http://vast-endpoint:8080/health

# Verify credentials
echo $VAST_ACCESS_KEY
echo $VAST_SECRET_KEY

# Check network
telnet vast-endpoint 8080
```

**S3 Connection Failed**
```bash
# Check S3 endpoint
curl http://s3-endpoint:9000/minio/health/live

# Verify credentials
echo $S3_ACCESS_KEY_ID
echo $S3_SECRET_ACCESS_KEY

# Test S3 operations
aws s3 ls --endpoint-url http://s3-endpoint:9000
```

#### Performance Issues

**Slow API Responses**
```bash
# Check metrics
curl http://localhost:8000/metrics | grep response_time

# Check database performance
curl http://localhost:8000/health

# Monitor resource usage
docker stats tams-api
```

**High Memory Usage**
```bash
# Check memory metrics
curl http://localhost:8000/metrics | grep memory

# Restart with more memory
docker run -m 4g tams-api
```

### Debug Mode

Enable debug logging:

```bash
# Set debug level
export LOG_LEVEL=DEBUG

# Or in docker-compose
environment:
  - LOG_LEVEL=DEBUG
```

### Health Checks

```bash
# Basic health check
curl http://localhost:8000/health

# Detailed health check
curl http://localhost:8000/health | jq .

# Check specific components
curl http://localhost:8000/health | jq '.dependencies'
```

### Logs

#### Application Logs
```bash
# View application logs
docker logs tams-api

# Follow logs
docker logs -f tams-api

# Filter logs
docker logs tams-api | grep ERROR
```

#### System Logs
```bash
# Check system logs
journalctl -u tams-api

# Check container logs
kubectl logs -f deployment/tams-api
```

### Recovery Procedures

#### Restart Services
```bash
# Restart application
docker-compose restart tams-api

# Or in Kubernetes
kubectl rollout restart deployment/tams-api
```

#### Database Recovery
```bash
# Check database status
curl http://vast-endpoint:8080/health

# Restart database
docker-compose restart vast
```

#### S3 Recovery
```bash
# Check S3 status
curl http://s3-endpoint:9000/minio/health/live

# Restart S3
docker-compose restart minio
```

## 📚 Additional Resources

- **[Usage Guide](USAGE.md)** - Comprehensive usage examples
- **[Architecture Guide](ARCHITECTURE.md)** - Technical architecture details
- **[API Reference](API_REFERENCE.md)** - Complete API documentation
- **[Observability Guide](OBSERVABILITY.md)** - Monitoring and observability
- **[Soft Delete Extension](SOFT_DELETE_EXTENSION.md)** - Soft delete functionality
- **[Docker Documentation](https://docs.docker.com/)** - Docker reference
- **[Kubernetes Documentation](https://kubernetes.io/docs/)** - K8s reference
- **[Prometheus Documentation](https://prometheus.io/docs/)** - Monitoring reference
- **[Grafana Documentation](https://grafana.com/docs/)** - Dashboard reference
