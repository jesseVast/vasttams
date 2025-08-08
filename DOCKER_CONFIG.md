# Docker Configuration Guide for TAMS API

This guide explains how to deploy and configure the TAMS API using Docker with different configuration methods.

## 🔧 Configuration Methods

### Method 1: Environment Variables (Development)

**Use Case**: Development, testing, simple deployments

**Example**:
```bash
# Run with environment variables
docker run -p 8000:8000 \
  -e VAST_ENDPOINT=http://172.200.204.90 \
  -e VAST_BUCKET=jthaloor-db \
  -e S3_ENDPOINT_URL=http://172.200.204.91 \
  -e S3_BUCKET_NAME=jthaloor-s3 \
  tams-api:latest
```

**Pros**:
- Simple and direct
- Easy to override
- Good for development

**Cons**:
- Variables visible in process list
- Not suitable for secrets in production

### Method 2: Environment File (Production)

**Use Case**: Production deployments, CI/CD pipelines

**Create `.env` file**:
```bash
# TAMS API Configuration
VAST_ENDPOINT=http://172.200.204.90
VAST_ACCESS_KEY=your-access-key
VAST_SECRET_KEY=your-secret-key
VAST_BUCKET=jthaloor-db
VAST_SCHEMA=tams

S3_ENDPOINT_URL=http://172.200.204.91
S3_ACCESS_KEY_ID=your-s3-access-key
S3_SECRET_ACCESS_KEY=your-s3-secret
S3_BUCKET_NAME=jthaloor-s3
S3_USE_SSL=false

API_TITLE=TAMS API
API_VERSION=6.0
HOST=0.0.0.0
PORT=8000
DEBUG=false
LOG_LEVEL=INFO
```

**Docker Compose**:
```yaml
version: '3.8'
services:
  tams-api:
    image: tams-api:latest
    ports:
      - "8000:8000"
    env_file:
      - .env
    restart: unless-stopped
```

**Pros**:
- Clean separation of config from code
- Easy to manage different environments
- Can be versioned (without secrets)

**Cons**:
- Secrets still in plain text file
- File needs proper permissions

### Method 3: Mounted Configuration (Enterprise)

**Use Case**: Enterprise deployments, Kubernetes, secure environments

**Create `config.json` file**:
```json
{
  "vast_endpoint": "http://172.200.204.90",
  "vast_access_key": "your-access-key",
  "vast_secret_key": "your-secret-key",
  "vast_bucket": "jthaloor-db",
  "vast_schema": "tams",
  "s3_endpoint_url": "http://172.200.204.91",
  "s3_access_key_id": "your-s3-access-key",
  "s3_secret_access_key": "your-s3-secret",
  "s3_bucket_name": "jthaloor-s3",
  "s3_use_ssl": false,
  "api_title": "TAMS API",
  "api_version": "6.0",
  "host": "0.0.0.0",
  "port": 8000,
  "debug": false,
  "log_level": "INFO"
}
```

**Docker Compose with mounted config**:
```yaml
version: '3.8'
services:
  tams-api:
    image: tams-api:latest
    ports:
      - "8000:8000"
    volumes:
      - ./config.json:/etc/tams/config.json:ro
    restart: unless-stopped
```

**Pros**:
- Most secure (can use encrypted volumes)
- Supports complex configuration structures
- Works well with Kubernetes ConfigMaps
- Read-only mounting for security

**Cons**:
- Slightly more complex setup
- Requires config file management

## 🚀 Quick Start Examples

### Development Setup
```bash
# Clone repository
git clone <repository-url>
cd bbctams

# Build Docker image
docker build -t tams-api:latest .

# Run with environment variables
docker run -p 8000:8000 \
  -e VAST_ENDPOINT=http://172.200.204.90 \
  -e VAST_BUCKET=jthaloor-db \
  -e S3_ENDPOINT_URL=http://172.200.204.91 \
  -e S3_BUCKET_NAME=jthaloor-s3 \
  tams-api:latest
```

### Production Setup with Docker Compose
```bash
# Create .env file with your configuration
cp env.example .env
nano .env

# Start services
docker-compose up -d

# Check logs
docker-compose logs -f tams-api
```

### Kubernetes Deployment
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: tams-config
  namespace: tams
data:
  config.json: |
    {
      "vast_endpoint": "http://172.200.204.90",
      "vast_bucket": "jthaloor-db",
      "s3_endpoint_url": "http://172.200.204.91",
      "s3_bucket_name": "jthaloor-s3"
    }
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: tams-api
  namespace: tams
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
        volumeMounts:
        - name: config
          mountPath: /etc/tams/config.json
          subPath: config.json
          readOnly: true
      volumes:
      - name: config
        configMap:
          name: tams-config
```

## 📋 Configuration Options

### Core API Settings
| Variable | Default | Description |
|----------|---------|-------------|
| `API_TITLE` | "TAMS API" | API service name |
| `API_VERSION` | "6.0" | API version |
| `API_DESCRIPTION` | "Time-addressable Media Store API" | API description |
| `HOST` | "0.0.0.0" | Bind address |
| `PORT` | 8000 | Port number |
| `DEBUG` | true | Debug mode |
| `LOG_LEVEL` | "INFO" | Logging level |

### VAST Database Settings
| Variable | Default | Description |
|----------|---------|-------------|
| `VAST_ENDPOINT` | "http://172.200.204.90" | VAST cluster endpoint |
| `VAST_ACCESS_KEY` | "" | VAST access key |
| `VAST_SECRET_KEY` | "" | VAST secret key |
| `VAST_BUCKET` | "jthaloor-db" | Database bucket name |
| `VAST_SCHEMA` | "tams" | Database schema name |

### S3 Storage Settings
| Variable | Default | Description |
|----------|---------|-------------|
| `S3_ENDPOINT_URL` | "http://172.200.204.91" | S3 endpoint |
| `S3_ACCESS_KEY_ID` | "" | S3 access key |
| `S3_SECRET_ACCESS_KEY` | "" | S3 secret key |
| `S3_BUCKET_NAME` | "jthaloor-s3" | S3 bucket for media segments |
| `S3_USE_SSL` | false | Use SSL for S3 connections |

## 🔐 Security Best Practices

### 1. Environment Variables
- Use Docker secrets for sensitive data
- Set proper file permissions (600) for .env files
- Never commit .env files with real secrets

### 2. Mounted Configuration
- Use read-only mounts (`:ro`)
- Store config files outside the container
- Use encrypted volumes for sensitive configs

### 3. Production Deployment
- Run as non-root user
- Use health checks
- Implement proper logging
- Set resource limits

### 4. Kubernetes Security
```yaml
# Security context example
securityContext:
  runAsNonRoot: true
  runAsUser: 1000
  runAsGroup: 1000
  fsGroup: 1000
  capabilities:
    drop:
    - ALL
  readOnlyRootFilesystem: true

# Resource limits
resources:
  limits:
    memory: "512Mi"
    cpu: "500m"
  requests:
    memory: "256Mi"
    cpu: "250m"
```

## 🔄 Configuration Priority

The TAMS API loads configuration in this order (highest to lowest priority):

1. **Mounted config file** (`/etc/tams/config.json`)
2. **Environment variables** (from .env or docker environment)
3. **Default values** (hardcoded in config.py)

This means mounted configs override environment variables, which override defaults.

## 🧪 Testing Configuration

### Health Check
```bash
curl http://localhost:8000/health
```

### Verify Database Connection
```bash
# Check if tables are created
curl http://localhost:8000/sources
curl http://localhost:8000/flows
```

### Test Configuration Loading
```bash
docker exec -it <container-id> python -c "
from app.config import get_settings
settings = get_settings()
print(f'VAST: {settings.vast_endpoint}')
print(f'S3: {settings.s3_endpoint_url}')
print(f'DB Bucket: {settings.vast_bucket}')
print(f'S3 Bucket: {settings.s3_bucket_name}')
"
```

### Integration Test
```bash
# Test full workflow
python tests/test_integration_api.py
```

## 📊 Monitoring and Logging

### Docker Compose with Logging
```yaml
version: '3.8'
services:
  tams-api:
    image: tams-api:latest
    ports:
      - "8000:8000"
    env_file:
      - .env
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    restart: unless-stopped
```

### Health Check Endpoint
The API provides a comprehensive health check at `/health`:
```json
{
  "status": "healthy",
  "timestamp": "2025-08-08T00:44:57.225303+00:00",
  "version": "6.0",
  "system": {
    "memory_usage_bytes": 7505166336,
    "memory_total_bytes": 17179869184,
    "cpu_percent": 23.0,
    "uptime_seconds": 2313.22531414032
  },
  "telemetry": {
    "tracing_enabled": true,
    "metrics_enabled": true
  }
}
```

## 🛠️ Troubleshooting

### Common Issues

1. **Database Connection Failed**
   - Check VAST_ENDPOINT is accessible
   - Verify access keys are correct
   - Ensure bucket exists

2. **S3 Storage Issues**
   - Check S3_ENDPOINT_URL is accessible
   - Verify S3 credentials
   - Ensure bucket exists and is accessible

3. **Permission Errors**
   - Check file permissions on mounted configs
   - Verify container runs with correct user

4. **Port Conflicts**
   - Change PORT environment variable
   - Update port mapping in Docker compose

### Debug Mode
Enable debug mode for detailed logging:
```bash
docker run -e DEBUG=true -e LOG_LEVEL=DEBUG tams-api:latest
```

## 📝 Example Configurations

### Development (Local VAST)
```bash
VAST_ENDPOINT=http://localhost:9090
VAST_BUCKET=dev-tams-db
S3_ENDPOINT_URL=http://localhost:9000
S3_BUCKET_NAME=dev-tams-s3
DEBUG=true
```

### Staging Environment
```bash
VAST_ENDPOINT=http://staging-vast.company.com
VAST_BUCKET=staging-tams-db
S3_ENDPOINT_URL=http://staging-s3.company.com
S3_BUCKET_NAME=staging-tams-s3
DEBUG=false
LOG_LEVEL=INFO
```

### Production Environment
```bash
VAST_ENDPOINT=http://prod-vast.company.com
VAST_BUCKET=prod-tams-db
S3_ENDPOINT_URL=http://prod-s3.company.com
S3_BUCKET_NAME=prod-tams-s3
DEBUG=false
LOG_LEVEL=WARNING
```

---

**For more details, see the main README and API documentation at `/docs` when the service is running.**
