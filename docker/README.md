# Docker Guide for TAMS API

This guide covers everything you need to know about using Docker with the TAMS (Time-addressable Media Store) API project.

## 🚀 **Quick Start**

### **Prerequisites**
- Docker Desktop installed and running
- Docker Compose v2+ (included with Docker Desktop)
- At least 4GB RAM available for Docker

### **Start Everything**
```bash
# From the project root directory
cd docker
docker-compose up -d
```

### **Check Status**
```bash
docker-compose ps
docker-compose logs -f
```

### **Stop Everything**
```bash
docker-compose down
```

## 📁 **File Structure**

```
docker/
├── README.md                           # This guide
├── Dockerfile                          # TAMS API server container definition
├── Dockerfile.ui                      # TAMS UI container definition
├── nginx.conf                          # Nginx configuration for UI
├── docker-compose.yml                  # Unified compose file (use profiles for dev/prod)
├── docker-compose.observability.yml    # Full observability stack
├── docker.env                          # Environment variables
├── config/
│   └── production.json.example         # Example production config
├── haproxy/
│   └── haproxy.cfg                     # HAProxy S3 proxy configuration
├── trino/
│   └── vast.properties                 # Trino VAST connector configuration
└── start-observability.sh              # Observability startup script
```

## 🔧 **Configuration Methods**

### **Method 1: Development (Server Only)**
```bash
# Development mode - server only, with Trino
cd docker
docker-compose --profile dev up -d
```

**Features:**
- ✅ Server + Trino for local development
- ✅ Uses local `config/config.json`
- ✅ Fast startup
- ✅ Easy debugging
- ❌ No UI (run UI separately with `npm start` for hot-reload)

### **Method 2: Production (Server + UI)**
```bash
# Production mode - server and UI
cd docker
# Create production config
cp config/production.json.example config/production.json
# Edit config/production.json with your settings
CONFIG_FILE=./config/production.json docker-compose --profile prod up -d
```

**Features:**
- ✅ Both server and UI containers
- ✅ HAProxy S3 proxy (clients don't talk directly to S3)
- ✅ Config file mounted at `/etc/tams/config.json`
- ✅ Production-ready
- ✅ No Trino (assumes external)
- ✅ Works with Kubernetes

### **Method 3: Full Stack (Server + UI + Trino)**
```bash
# Full stack - everything for local testing
cd docker
docker-compose --profile full up -d
```

**Features:**
- ✅ Server + UI + Trino + HAProxy
- ✅ Complete local environment
- ✅ Good for integration testing

### **Method 4: Full Observability Stack**
```bash
# Uses docker-compose.observability.yml for complete monitoring
cd docker
docker-compose -f docker-compose.observability.yml up -d
```

**Features:**
- ✅ Complete monitoring stack
- ✅ Prometheus + Grafana + Jaeger
- ✅ Production-ready observability
- ❌ Higher resource usage

## 🐳 **Container Details**

### **TAMS API Server Container**
- **Base Image**: `python:3.12-slim`
- **Port**: 8000 (internal), mapped to host
- **Health Check**: `/health` endpoint
- **Dependencies**: VAST database, S3 storage
- **Config**: Mounted at `/etc/tams/config.json` (read-only)
- **Structure**: Uses `src/server/` package structure

### **TAMS UI Container**
- **Base Image**: `node:20-alpine` (build), `nginx:alpine` (runtime)
- **Port**: 80 (internal), mapped to host
- **Health Check**: `/health` endpoint
- **Build**: Multi-stage build (React build + Nginx serve)
- **Proxy**: API requests proxied to `tams-api:8000`

### **HAProxy S3 Proxy Container**
- **Base Image**: `haproxy:latest`
- **Port**: 4001 (default, configurable via `HAPROXY_PORT`)
- **Purpose**: Proxies S3 requests so clients don't talk directly to S3
- **Config**: `haproxy/haproxy.cfg` mounted at `/usr/local/etc/haproxy/haproxy.cfg`
- **Features**:
  - Handles presigned URL authentication
  - Load balances across multiple S3 VIPs
  - Custom DNS resolver support
- **Profiles**: `prod`, `full` (not in `dev` profile)

### **Observability Stack** (Profile: `observability`)
- **Prometheus**: Metrics collection (port 9090)
- **Grafana**: Dashboards (port 3000, admin/admin)
- **Jaeger**: Distributed tracing (port 16686)
- **Alertmanager**: Alert management (port 9093)
- **Node Exporter**: System metrics (port 9100)
- **Profiles**: `observability`, `full` (can be combined with `dev` or `prod`)

## 🔐 **Environment Configuration**

### **Required Environment Variables**
```bash
# VAST Database
VAST_ENDPOINT=http://your-vast-server:80
VAST_ACCESS_KEY=your-access-key
VAST_SECRET_KEY=your-secret-key
VAST_BUCKET=your-bucket
VAST_SCHEMA=your-schema

# S3 Storage
# Use HAProxy proxy in production (clients don't talk directly to S3)
S3_ENDPOINT_URL=http://tams-haproxy:80  # When using HAProxy
# Or direct S3 endpoint for development
# S3_ENDPOINT_URL=http://your-s3-server:9000
S3_ACCESS_KEY_ID=your-access-key
S3_SECRET_ACCESS_KEY=your-secret-key
S3_BUCKET_NAME=your-bucket
S3_REGION=us-east-1

# Application
DEBUG=false
LOG_LEVEL=INFO
API_HOST=0.0.0.0
API_PORT=8000
```

### **Optional Environment Variables**
```bash
# Authentication
JWT_SECRET_KEY=your-jwt-secret
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# Database
DATABASE_URL=postgresql://user:pass@host:5432/db

# Monitoring
ENABLE_TELEMETRY=true
METRICS_PORT=9090

# HAProxy Configuration
HAPROXY_PORT=4001              # Port to expose HAProxy on host (default: 4001)
HAPROXY_DNS=10.140.3.248      # DNS resolver for HAProxy (default: 10.140.3.248)
```

## 🚀 **Deployment Scenarios**

### **Local Development**
```bash
cd docker
# Development mode (server + Trino, no UI)
docker-compose --profile dev up -d

# With observability stack
docker-compose --profile dev --profile observability up -d
```

**Access Points:**
- TAMS API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/health
- Trino: http://localhost:8080

**With Observability:**
- Grafana: http://localhost:3000 (admin/admin)
- Prometheus: http://localhost:9090
- Jaeger: http://localhost:16686
- Alertmanager: http://localhost:9093

**Note**: For development, run the UI separately with `npm start` in the `ui/` directory for hot-reload.

### **Production Deployment**
```bash
cd docker
# Create production config from example
cp config/production.json.example config/production.json
# Edit config/production.json with your production settings
CONFIG_FILE=./config/production.json docker-compose --profile prod up -d

# With observability stack
CONFIG_FILE=./config/production.json docker-compose --profile prod --profile observability up -d
```

**Features:**
- Both server and UI containers
- HAProxy S3 proxy (clients use `tams-haproxy:80` instead of direct S3)
- Config file mounted at `/etc/tams/config.json`
- Restart policy: unless-stopped
- Health checks enabled for all services
- Logging configured
- UI proxies API requests to backend

**Access Points:**
- TAMS UI: http://localhost (port 80)
- TAMS API: http://localhost:8000 (direct access)
- HAProxy S3 Proxy: http://localhost:4001 (default, configurable)
- API Docs: http://localhost:8000/docs

**With Observability:**
- Grafana: http://localhost:3000 (admin/admin)
- Prometheus: http://localhost:9090
- Jaeger: http://localhost:16686
- Alertmanager: http://localhost:9093
- Health Check: http://localhost:8000/health

**Note**: Configure your S3 endpoint in `production.json` to use `http://tams-haproxy:80` so clients route through HAProxy instead of directly to S3.

### **Config File Mounting**

The production docker-compose mounts `config/production.json` to `/etc/tams/config.json` in the container. The application automatically loads this file if it exists, otherwise falls back to `config/config.json` for local development.

**Config File Location:**
- Container path: `/etc/tams/config.json` (read-only mount)
- Local path: `docker/config/production.json`
- Example: `docker/config/production.json.example`

**Creating Production Config:**
```bash
cd docker
cp config/production.json.example config/production.json
# Edit config/production.json with your settings
# DO NOT commit production.json to git (contains secrets)
```

### **Full Stack with Observability**
```bash
cd docker
# Full stack: dev + prod + observability
docker-compose --profile full up -d

# Or combine profiles manually
docker-compose --profile dev --profile prod --profile observability up -d
```

**Access Points:**
- TAMS UI: http://localhost (port 80)
- TAMS API: http://localhost:8000
- Grafana: http://localhost:3000 (admin/admin)
- Prometheus: http://localhost:9090
- Jaeger: http://localhost:16686
- Alertmanager: http://localhost:9093

## 🔍 **Troubleshooting**

### **Common Issues**

#### **Container Won't Start**
```bash
# Check logs
docker-compose logs

# Check resource usage
docker stats

# Restart containers
docker-compose restart
```

#### **Port Already in Use**
```bash
# Find what's using the port
lsof -i :8000

# Stop conflicting service
sudo systemctl stop conflicting-service

# Or change ports in docker-compose.yml
```

#### **Database Connection Issues**
```bash
# Check VAST database connectivity
docker exec -it tams-api ping vast-server

# Check environment variables
docker exec -it tams-api env | grep VAST

# Test connection from container
docker exec -it tams-api python -c "import vastdb; print('Connected')"
```

#### **S3 Connection Issues**
```bash
# Check S3 credentials
docker exec -it tams-api env | grep S3

# Test S3 connectivity
docker exec -it tams-api python -c "import boto3; print('S3 OK')"
```

### **Debug Mode**
```bash
# Enable debug logging
export DEBUG=true
docker-compose up

# Or edit docker.env
echo "DEBUG=true" >> docker.env
docker-compose up
```

### **Resource Issues**
```bash
# Check container resources
docker stats

# Increase Docker Desktop resources
# Docker Desktop → Settings → Resources → Advanced

# Monitor system resources
htop
df -h
free -h
```

## 📊 **Monitoring & Logs**

### **Container Logs**
```bash
# All containers
docker-compose logs

# Specific service
docker-compose logs tams-api

# Follow logs
docker-compose logs -f tams-api

# Last 100 lines
docker-compose logs --tail=100 tams-api
```

### **Container Status**
```bash
# Running containers
docker-compose ps

# All containers (including stopped)
docker-compose ps -a

# Resource usage
docker stats
```

### **Health Checks**
```bash
# Check API health
curl http://localhost:8000/health

# Check container health
docker inspect tams-api | grep Health -A 10
```

## 🔄 **Maintenance**

### **Update Images**
```bash
# Pull latest images
docker-compose pull

# Rebuild with latest code
docker-compose build --no-cache

# Restart services
docker-compose up -d
```

### **Clean Up**
```bash
# Remove stopped containers
docker container prune

# Remove unused images
docker image prune

# Remove unused volumes
docker volume prune

# Remove unused networks
docker network prune

# Complete cleanup (careful!)
docker system prune -a
```

### **Backup & Restore**
```bash
# Backup volumes
docker run --rm -v tams_data:/data -v $(pwd):/backup alpine tar czf /backup/tams_backup.tar.gz -C /data .

# Restore volumes
docker run --rm -v tams_data:/data -v $(pwd):/backup alpine tar xzf /backup/tams_backup.tar.gz -C /data
```

## 🚀 **Advanced Usage**

### **Custom Dockerfile**
```dockerfile
# Example custom Dockerfile
FROM python:3.12-slim

# Install custom dependencies
RUN apt-get update && apt-get install -y \
    custom-package \
    && rm -rf /var/lib/apt/lists/*

# Copy application
COPY . /app
WORKDIR /app

# Install Python dependencies
RUN pip install -r requirements.txt

# Expose port
EXPOSE 8000

# Start application
CMD ["python", "run.py"]
```

### **Multi-Stage Builds**
```dockerfile
# Build stage
FROM python:3.12-slim as builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --user -r requirements.txt

# Runtime stage
FROM python:3.12-slim
COPY --from=builder /root/.local /root/.local
COPY . /app
WORKDIR /app
EXPOSE 8000
CMD ["python", "run.py"]
```

### **Docker Compose Overrides**
```yaml
# docker-compose.override.yml
version: '3.8'
services:
  tams-api:
    environment:
      - DEBUG=true
      - LOG_LEVEL=DEBUG
    volumes:
      - .:/app
      - /app/__pycache__
```

## 📚 **Best Practices**

### **Security**
- ✅ Use `.env` files for secrets (not in git)
- ✅ Implement health checks
- ✅ Use non-root users
- ✅ Scan images for vulnerabilities
- ❌ Don't expose unnecessary ports
- ❌ Don't run containers as root

### **Performance**
- ✅ Use multi-stage builds
- ✅ Optimize layer caching
- ✅ Set resource limits
- ✅ Use appropriate base images
- ❌ Don't install unnecessary packages
- ❌ Don't copy unnecessary files

### **Maintenance**
- ✅ Tag images with versions
- ✅ Use specific base image tags
- ✅ Regular security updates
- ✅ Monitor resource usage
- ❌ Don't use `latest` tags in production
- ❌ Don't ignore security warnings

## 🆘 **Getting Help**

### **Useful Commands**
```bash
# Inspect container
docker inspect tams-api

# Execute commands in container
docker exec -it tams-api bash

# Copy files to/from container
docker cp tams-api:/app/logs ./logs

# View container filesystem
docker exec -it tams-api ls -la /app
```

### **Resources**
- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Reference](https://docs.docker.com/compose/)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [TAMS Project Issues](https://github.com/your-repo/issues)

### **Common Patterns**
```bash
# Development workflow (server + Trino)
docker-compose --profile dev up -d
# Make code changes
docker-compose restart tams-api

# Production deployment (server + UI)
CONFIG_FILE=./config/production.json docker-compose --profile prod up -d

# Full stack (server + UI + Trino)
docker-compose --profile full up -d

# Debug mode
docker-compose logs -f tams-api
docker exec -it tams-api bash
```

---

*Last Updated: August 2024*
*Version: 1.0*
