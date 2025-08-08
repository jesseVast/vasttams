# Docker Configuration Guide for TAMS API

This guide explains how to pass configuration to the TAMS API Docker container using different methods.

## 🔧 Configuration Methods

### Method 1: Environment Variables (Development)

**Use Case**: Development, testing, simple deployments

**Files**: `docker-compose.yml` (updated)

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

### Method 2: Environment File (Production)

**Use Case**: Production deployments, CI/CD pipelines

**Files**: `docker.env`, `docker-compose.prod.yml`

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

### Method 3: Mounted Configuration (Enterprise)

**Use Case**: Enterprise deployments, Kubernetes, secure environments

**Files**: `config/production.json`, `docker-compose.config.yml`

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

## 🚀 Quick Start

### For Development
```bash
# Use the updated docker-compose.yml
docker-compose up
```

### For Production with Environment File
```bash
cp docker.env .env
# Edit .env with your production settings
docker-compose -f docker-compose.prod.yml up -d
```

### For Production with Mounted Config
```bash
# Edit config/production.json with your settings
docker-compose -f docker-compose.config.yml up -d
```

## 🔐 Security Best Practices

### 1. Environment Variables
- Use Docker secrets for sensitive data
- Set proper file permissions (600) for .env files
- Never commit .env files with real secrets

### 2. Mounted Configuration
- Use read-only mounts (`:ro`)
- Store config files outside the container
- Use encrypted volumes for sensitive configs

### 3. Kubernetes Deployment
Your existing Kubernetes setup already uses ConfigMaps:
```yaml
# From k8s/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: tams-config
  namespace: tams
data:
  config.json: |
    {
      "vast_endpoint": "http://172.200.204.90",
      "s3_endpoint_url": "http://172.200.204.91",
      ...
    }
```

## 📁 File Overview

| File | Purpose | Method |
|------|---------|---------|
| `docker-compose.yml` | Development with env vars | Method 1 |
| `docker-compose.prod.yml` | Production with env file | Method 2 |
| `docker-compose.config.yml` | Production with mounted config | Method 3 |
| `docker.env` | Environment variables template | Method 2 |
| `config/production.json` | JSON configuration file | Method 3 |
| `k8s/configmap.yaml` | Kubernetes ConfigMap | Method 3 |

## 🔄 Configuration Priority

Your `config.py` loads configuration in this order (highest to lowest priority):

1. **Mounted config file** (`/etc/tams/config.json`)
2. **Environment variables** (from .env or docker environment)
3. **Default values** (hardcoded in config.py)

This means mounted configs override environment variables, which override defaults.

## 🧪 Testing Configuration

Test your configuration with:
```bash
# Test database connectivity
docker-compose exec tams-api python mgmt/test_db_connection.py

# Check configuration loading
docker-compose exec tams-api python -c "
from app.core.config import get_settings
settings = get_settings()
print(f'VAST: {settings.vast_endpoint}')
print(f'S3: {settings.s3_endpoint_url}')
"
```

## 📝 Notes

- All three methods work with your current `app/core/config.py`
- The configuration system is already implemented and tested
- Choose the method that best fits your deployment environment
- You can combine methods (e.g., use env vars for non-secrets, mounted config for secrets)
