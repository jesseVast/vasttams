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
├── Dockerfile                          # TAMS API container definition
├── docker-compose.yml                  # Development environment
├── docker-compose.prod.yml             # Production environment
├── docker-compose.config.yml           # Enterprise config mounting
├── docker-compose.observability.yml    # Full observability stack
├── docker.env                          # Environment variables
└── start-observability.sh              # Observability startup script
```

## 🔧 **Configuration Methods**

### **Method 1: Development (Default)**
```bash
# Uses docker-compose.yml with environment variables
cd docker
docker-compose up
```

**Features:**
- ✅ Fast startup
- ✅ Easy debugging
- ✅ Environment variable overrides
- ❌ Not suitable for production

### **Method 2: Production with Environment File**
```bash
# Uses docker-compose.prod.yml with docker.env
cd docker
cp docker.env .env
# Edit .env with your production values
docker-compose -f docker-compose.prod.yml up -d
```

**Features:**
- ✅ Production-ready
- ✅ Environment-specific configuration
- ✅ Can be versioned (without secrets)
- ❌ Secrets in plain text

### **Method 3: Enterprise with Mounted Config**
```bash
# Uses docker-compose.config.yml with mounted config files
cd docker
# Edit ../config/production.json with your settings
docker-compose -f docker-compose.config.yml up -d
```

**Features:**
- ✅ Most secure
- ✅ Complex configuration support
- ✅ Works with Kubernetes
- ❌ More complex setup

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

### **TAMS API Container**
- **Base Image**: `python:3.12-slim`
- **Port**: 8000 (internal), mapped to host
- **Health Check**: `/health` endpoint
- **Dependencies**: VAST database, S3 storage

### **Observability Stack**
- **Prometheus**: Metrics collection (port 9090)
- **Grafana**: Dashboards (port 3000, admin/admin)
- **Jaeger**: Distributed tracing (port 16686)
- **Alertmanager**: Alert management (port 9093)

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
S3_ENDPOINT_URL=http://your-s3-server:9000
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
```

## 🚀 **Deployment Scenarios**

### **Local Development**
```bash
cd docker
docker-compose up
```

**Access Points:**
- TAMS API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

### **Production Deployment**
```bash
cd docker
cp docker.env .env
# Edit .env with production values
docker-compose -f docker-compose.prod.yml up -d
```

**Features:**
- Restart policy: always
- Resource limits configured
- Health checks enabled
- Logging configured

### **Enterprise Deployment**
```bash
cd docker
# Create production config
cp ../config/production.json ../config/production-custom.json
# Edit production-custom.json
docker-compose -f docker-compose.config.yml up -d
```

**Features:**
- Mounted configuration files
- Encrypted volume support
- Kubernetes compatibility
- Advanced security

### **Full Monitoring Stack**
```bash
cd docker
docker-compose -f docker-compose.observability.yml up -d
```

**Access Points:**
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
# Development workflow
docker-compose up -d
# Make code changes
docker-compose restart tams-api

# Production deployment
docker-compose -f docker-compose.prod.yml up -d

# Debug mode
docker-compose logs -f tams-api
docker exec -it tams-api bash
```

---

*Last Updated: August 2024*
*Version: 1.0*
