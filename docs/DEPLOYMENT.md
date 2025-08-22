# TAMS Deployment Documentation

This document consolidates all deployment-related information for the TAMS (Time-addressable Media Store) API.

## 🐳 **Docker Configuration Guide**

### **Configuration Methods**

#### **Method 1: Environment Variables (Development)**

**Use Case**: Development, testing, simple deployments

**Files**: `docker/docker-compose.yml` (updated)

```bash
# Run with environment variables
docker-compose up
```

**Pros**:
- Simple and direct
- Easy to override
- Good for development

**Cons**:
- Variables visible in process list
- Not suitable for secrets in production

#### **Method 2: Environment File (Production)**

**Use Case**: Production deployments, CI/CD pipelines

**Files**: `docker/docker.env`, `docker/docker-compose.prod.yml`

```bash
# Copy and customize the environment file
cp docker.env .env
# Edit .env with your production values
nano .env

# Run with environment file
docker-compose -f docker-compose.prod.yml up
```

**Pros**:
- Clean separation of config from code
- Easy to manage different environments
- Can be versioned (without secrets)

**Cons**:
- Secrets still in plain text file
- File needs proper permissions

#### **Method 3: Mounted Configuration (Enterprise)**

**Use Case**: Enterprise deployments, Kubernetes, secure environments

**Files**: `config/production.json`, `docker/docker-compose.config.yml`

```bash
# Customize the config file
nano config/production.json

# Run with mounted config
docker-compose -f docker-compose.config.yml up
```

**Pros**:
- Most secure (can use encrypted volumes)
- Supports complex configuration structures
- Already implemented in your config.py
- Works well with Kubernetes ConfigMaps

**Cons**:
- Slightly more complex setup
- Requires config file management

### **Quick Start**

#### **For Development**
```bash
# Use the updated docker/docker-compose.yml
cd docker
docker-compose up
```

#### **For Production with Environment File**
```bash
cp docker/docker.env .env
# Edit .env with your production settings
docker-compose -f docker/docker-compose.prod.yml up -d
```

#### **For Production with Mounted Config**
```bash
# Edit config/production.json with your settings
docker-compose -f docker/docker-compose.config.yml up -d
```

### **Security Best Practices**

#### **1. Environment Variables**
- Use Docker secrets for sensitive data
- Avoid hardcoding secrets in docker-compose files
- Use .env files for non-sensitive configuration

#### **2. Configuration Files**
- Mount configuration files from secure volumes
- Use encrypted volumes for sensitive data
- Implement proper file permissions

#### **3. Network Security**
- Use internal networks for inter-service communication
- Expose only necessary ports
- Implement proper firewall rules

## 📊 **Observability Stack**

### **Quick Start**

#### **Start the Observability Stack**
```bash
./start-observability.sh
```

#### **Access Points**
- **Grafana Dashboard**: http://localhost:3000
  - **Username:** admin
  - **Password:** admin
- **Prometheus**: http://localhost:9090
- **Jaeger Tracing**: http://localhost:16686
- **Alertmanager**: http://localhost:9093
- **TAMS Metrics**: http://localhost:8000/metrics
- **TAMS Health**: http://localhost:8000/health

### **Telemetry Features**

#### **1. Prometheus Metrics**

The TAMS API exposes comprehensive Prometheus metrics at `/metrics`:

##### **HTTP Metrics**
- `tams_http_requests_total` - Total HTTP requests by method, endpoint, and status code
- `tams_http_request_duration_seconds` - Request duration histograms
- `tams_errors_total` - Error counts by type and endpoint

##### **Business Metrics**
- `tams_sources_total` - Total number of sources
- `tams_flows_total` - Total number of flows
- `tams_segments_total` - Total number of flow segments
- `tams_storage_bytes_total` - Total storage usage in bytes

##### **Operation Metrics**
- `tams_flow_operations_total` - Flow operations by type, format, and status
- `tams_segment_operations_total` - Segment operations by type and status
- `tams_source_operations_total` - Source operations by type, format, and status

##### **Performance Metrics**
- `tams_vast_query_duration_seconds` - VAST database query performance
- `tams_s3_operation_duration_seconds` - S3 operation performance

##### **System Metrics**
- `tams_memory_usage_bytes` - Memory usage
- `tams_active_connections` - Active database connections

#### **2. OpenTelemetry Tracing**

Distributed tracing is implemented using OpenTelemetry:

##### **Trace Features**
- Automatic instrumentation of FastAPI endpoints
- Custom spans for business operations
- Correlation IDs for request tracking
- Integration with Jaeger for trace visualization

##### **Trace Decorators**
```python
from app.telemetry import trace_operation

@trace_operation("flow_creation")
async def create_flow(flow_data):
    # Operation will be traced automatically
    pass
```

#### **3. Enhanced Logging**

- Structured logging with correlation IDs
- Configurable log levels and formats
- Integration with OpenTelemetry logging instrumentation

#### **4. Health Checks**

Enhanced health check endpoint at `/health` includes:
- Application status
- System metrics (CPU, memory, uptime)
- Telemetry status
- Version information

### **Architecture**

#### **Components**

1. **TAMS API** - Main application with embedded telemetry
2. **Prometheus** - Metrics collection and storage
3. **Grafana** - Metrics visualization and dashboards
4. **Jaeger** - Distributed tracing visualization
5. **Alertmanager** - Alert management and routing
6. **Node Exporter** - System metrics collection

#### **Data Flow**

```
TAMS API → Prometheus Metrics → Grafana Dashboards
```

## 🚀 **Kubernetes Deployment**

### **Helm Charts**

The project includes Helm charts for Kubernetes deployment:

#### **Chart Structure**
```
helm/tams/
├── Chart.yaml
├── values.yaml
├── templates/
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── ingress.yaml
│   ├── configmap.yaml
│   ├── secrets.yaml
│   └── ...
└── README.md
```

#### **Deployment Commands**
```bash
# Install the chart
helm install tams ./helm/tams

# Upgrade existing deployment
helm upgrade tams ./helm/tams

# Uninstall
helm uninstall tams
```

### **Configuration**

#### **Environment-Specific Values**
```yaml
# values.yaml
replicaCount: 3
image:
  repository: tams-api
  tag: latest
  pullPolicy: IfNotPresent

resources:
  limits:
    cpu: 1000m
    memory: 1Gi
  requests:
    cpu: 500m
    memory: 512Mi

ingress:
  enabled: true
  className: nginx
  annotations:
    kubernetes.io/ingress.class: nginx
  hosts:
    - host: tams.example.com
      paths:
        - path: /
          pathType: Prefix
```

## 🔐 **Security Configuration**

### **Authentication**

#### **JWT Configuration**
```yaml
auth:
  jwt:
    secret_key: your-secret-key
    algorithm: HS256
    access_token_expire_minutes: 30
    refresh_token_expire_days: 7
```

#### **API Key Configuration**
```yaml
auth:
  api_keys:
    enabled: true
    header_name: X-API-Key
    rate_limit: 1000  # requests per hour
```

### **Network Security**

#### **NGINX Front-End for TLS Termination**

**Why NGINX?**
- Acts as a reverse proxy
- Handles HTTPS (TLS) termination
- Can enforce security headers and rate limiting

**Example NGINX Configuration**
```nginx
server {
    listen 443 ssl;
    server_name your.domain.com;

    ssl_certificate     /etc/nginx/certs/cert.pem;
    ssl_certificate_key /etc/nginx/certs/key.pem;

    location / {
        proxy_pass http://app:8000;  # FastAPI app
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**Running NGINX with Docker**
```yaml
services:
  nginx:
    image: nginx:alpine
    ports:
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/conf.d/default.conf:ro
      - ./cert.pem:/etc/nginx/certs/cert.pem:ro
      - ./key.pem:/etc/nginx/certs/key.pem:ro
    depends_on:
      - app
  app:
    build: .
    expose:
      - "8000"
```

#### **Self-Signed Certificates**

For development/testing, use the provided script:
```bash
./mgmt/generate_self_signed_cert.sh
```

#### **Firewall Rules**
```bash
# Allow only necessary ports
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
ufw allow 8000/tcp  # TAMS API
ufw enable
```

#### **SSL/TLS Configuration**
```yaml
ssl:
  enabled: true
  certificate_file: /etc/ssl/certs/tams.crt
  private_key_file: /etc/ssl/private/tams.key
  ca_certificate_file: /etc/ssl/certs/ca.crt
```

## 📋 **Deployment Checklist**

### **Pre-Deployment**
- [ ] Environment variables configured
- [ ] Database connection tested
- [ ] S3 credentials verified
- [ ] SSL certificates installed
- [ ] Firewall rules configured
- [ ] Monitoring stack deployed

### **Deployment**
- [ ] Docker images built and tagged
- [ ] Configuration files updated
- [ ] Secrets properly configured
- [ ] Health checks passing
- [ ] Metrics collection working
- [ ] Logs accessible

### **Post-Deployment**
- [ ] API endpoints responding
- [ ] Database operations working
- [ ] File uploads functional
- [ ] Monitoring dashboards populated
- [ ] Alerting configured
- [ ] Backup procedures tested

## 🆘 **Troubleshooting**

### **Common Issues**

#### **Connection Timeouts**
- Check network connectivity
- Verify firewall rules
- Check DNS resolution
- Verify endpoint URLs

#### **Authentication Failures**
- Verify JWT secret keys
- Check API key configuration
- Verify user credentials
- Check token expiration

#### **Performance Issues**
- Monitor resource usage
- Check database performance
- Verify cache configuration
- Review query optimization

### **Log Analysis**

#### **Log Locations**
```bash
# Application logs
docker logs tams-api

# System logs
journalctl -u tams-api

# Access logs
tail -f /var/log/nginx/access.log
```

#### **Key Log Patterns**
```bash
# Error logs
grep "ERROR" /var/log/tams/app.log

# Performance issues
grep "slow" /var/log/tams/app.log

# Authentication failures
grep "auth" /var/log/tams/app.log
```
