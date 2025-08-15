# TAMS API Kubernetes Deployment

This directory contains Kubernetes manifests for deploying the TAMS (Time-addressable Media Store) API service.

## Architecture Overview

The TAMS API is deployed as a scalable microservice with a modular architecture:

- **Namespace**: Isolated `tams` namespace for all TAMS resources
- **Secrets**: Secure storage for database credentials and API keys
- **ConfigMap**: Non-sensitive configuration values
- **Deployment**: Multi-replica application deployment with health checks
- **Service**: Internal cluster networking
- **Ingress**: External access with TLS termination
- **HPA**: Automatic scaling based on resource usage
- **PDB**: High availability during maintenance

### Application Architecture

The TAMS API follows a modular router architecture:
- **Core Application**: `main.py` handles lifespan management and service endpoints
- **Domain Routers**: Separate routers for flows, segments, sources, objects, and analytics
- **Business Logic**: Dedicated manager classes for each domain
- **Dependency Injection**: Centralized dependency management for VAST store access

## Prerequisites

1. **Kubernetes Cluster**: v1.24+ with the following components:
   - NGINX Ingress Controller
   - cert-manager (for TLS certificates)
   - Metrics Server (for HPA)

2. **External Dependencies**:
   - VAST Database service
   - VAST S3 storage service

3. **Docker Image**: Build and push the TAMS API image:
   ```bash
   docker build -t tams-api:latest .
   docker tag tams-api:latest your-registry/tams-api:latest
   docker push your-registry/tams-api:latest
   ```

## Security Configuration

### Secrets Management

The `secrets.yaml` file contains base64-encoded sensitive data. **IMPORTANT**: Replace the default values with your actual credentials:

```bash
# Generate base64 encoded secrets
echo -n "your-vast-access-key" | base64
echo -n "your-vast-secret-key" | base64
echo -n "your-s3-access-key" | base64
echo -n "your-s3-secret-key" | base64
```

### Security Features

- **Non-root containers**: Application runs as user 1000
- **Read-only filesystem**: Prevents file system tampering
- **Dropped capabilities**: Minimal container privileges
- **Resource limits**: Prevents resource exhaustion
- **Network policies**: Isolated network access (if configured)

## Deployment Steps

### 1. Create Namespace and Secrets

```bash
# Apply namespace and secrets first
kubectl apply -f namespace.yaml
kubectl apply -f secrets.yaml
```

### 2. Update Configuration

Edit `configmap.yaml` to match your environment:
- VAST Database endpoint
- S3 storage endpoint
- Application settings

### 3. Deploy Application

```bash
# Deploy all resources
kubectl apply -k .

# Or deploy individually
kubectl apply -f configmap.yaml
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml
kubectl apply -f ingress.yaml
kubectl apply -f hpa.yaml
kubectl apply -f pdb.yaml
```

### 4. Verify Deployment

```bash
# Check all resources
kubectl get all -n tams

# Check pod status
kubectl get pods -n tams

# Check logs
kubectl logs -f deployment/tams-api -n tams

# Test health endpoint
kubectl port-forward service/tams-api-service 8080:80 -n tams
curl http://localhost:8080/health

# Test analytics endpoint
curl http://localhost:8080/analytics/flow-usage
```

## Configuration

### Configuration Management

The TAMS API uses a hybrid configuration approach:

1. **Mounted Configuration File**: Non-sensitive configuration is mounted as `/etc/tams/config.json`
2. **Environment Variables**: Sensitive data (credentials) are passed as environment variables from secrets
3. **Default Values**: Fallback values are defined in the application code

### Configuration File Structure

The `config.json` file contains non-sensitive configuration:

```json
{
  "host": "0.0.0.0",
  "port": 8000,
  "debug": false,
  "vast_endpoint": "http://vast-service:8080",
  "vast_bucket": "tams-bucket",
          "vast_schema": "tams7",
  "s3_endpoint_url": "http://s3-service:9000",
  "s3_bucket_name": "tams-bucket",
  "s3_use_ssl": false,
  "log_level": "INFO",
  "log_format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
  "health_check_path": "/health",
  "health_check_interval": "30s",
  "health_check_timeout": "10s"
}
```

### Environment Variables (Secrets Only)

| Variable | Source | Description |
|----------|--------|-------------|
| `VAST_ACCESS_KEY` | Secret | VAST access key |
| `VAST_SECRET_KEY` | Secret | VAST secret key |
| `S3_ACCESS_KEY_ID` | Secret | S3 access key ID |
| `S3_SECRET_ACCESS_KEY` | Secret | S3 secret access key |

### Configuration Precedence

1. **Mounted config.json** (highest priority for non-sensitive config)
2. **Environment variables** (for secrets)
3. **Default values** (lowest priority)

### Updating Configuration

To update the configuration:

```bash
# Update non-sensitive config
kubectl patch configmap tams-config -n tams --patch '{"data":{"config.json":"{\"log_level\":\"DEBUG\",\"log_format\":\"json\"}"}}'

# Update secrets (if needed)
kubectl patch secret tams-secrets -n tams --patch '{"data":{"vast-access-key":"bmV3LWtleQ=="}}'

# Restart pods to pick up new config
kubectl rollout restart deployment/tams-api -n tams
```

### Scaling Configuration

- **Replicas**: 3 (minimum), 10 (maximum)
- **CPU**: 250m request, 500m limit
- **Memory**: 256Mi request, 512Mi limit
- **HPA**: Scales on 70% CPU and 80% memory utilization

## API Endpoints

### Core Endpoints
- `GET /health` - Health check
- `GET /` - Service information
- `GET /service` - Service configuration
- `GET /openapi.json` - OpenAPI specification

### Domain Endpoints
- `GET /sources` - Source management
- `GET /flows` - Flow management
- `GET /flows/{id}/segments` - Segment management
- `GET /objects` - Object management

### Analytics Endpoints
- `GET /analytics/flow-usage` - Flow usage statistics
- `GET /analytics/storage-usage` - Storage usage analysis
- `GET /analytics/time-range-analysis` - Time range patterns

### Management Endpoints
- `GET /service/webhooks` - Webhook management
- `GET /flow-delete-requests` - Deletion request management

## Monitoring and Logging

### Health Checks

- **Liveness Probe**: `/health` endpoint every 30s
- **Readiness Probe**: `/health` endpoint every 10s
- **Initial Delay**: 30s for liveness, 5s for readiness

### Metrics

The application exposes Prometheus metrics at `/metrics` (if configured).

### Logging

Logs are available via:
```bash
kubectl logs -f deployment/tams-api -n tams
```

## Troubleshooting

### Common Issues

1. **Pod CrashLoopBackOff**:
   ```bash
   kubectl describe pod <pod-name> -n tams
   kubectl logs <pod-name> -n tams
   ```

2. **Service Not Accessible**:
   ```bash
   kubectl get endpoints -n tams
   kubectl describe service tams-api-service -n tams
   ```

3. **Ingress Issues**:
   ```bash
   kubectl describe ingress tams-api-ingress -n tams
   kubectl get events -n tams
   ```

### Debug Commands

```bash
# Check resource usage
kubectl top pods -n tams

# Check HPA status
kubectl describe hpa tams-api-hpa -n tams

# Check events
kubectl get events -n tams --sort-by='.lastTimestamp'

# Port forward for debugging
kubectl port-forward service/tams-api-service 8080:80 -n tams
```

## Backup and Recovery

### Data Backup

The TAMS API stores data in:
- **VAST Database**: Metadata and analytics
- **S3 Storage**: Media segments

Ensure both are backed up according to your data retention policies.

### Configuration Backup

Backup Kubernetes resources:
```bash
kubectl get all -n tams -o yaml > tams-backup.yaml
kubectl get secrets -n tams -o yaml > tams-secrets-backup.yaml
```

## Updates and Rollouts

### Rolling Updates

```bash
# Update image
kubectl set image deployment/tams-api tams-api=your-registry/tams-api:v2 -n tams

# Monitor rollout
kubectl rollout status deployment/tams-api -n tams

# Rollback if needed
kubectl rollout undo deployment/tams-api -n tams
```

### Blue-Green Deployment

For zero-downtime deployments, consider implementing blue-green deployment patterns.

## Security Best Practices

1. **Rotate Secrets Regularly**: Update secrets periodically
2. **Network Policies**: Implement network policies for pod-to-pod communication
3. **RBAC**: Use appropriate service accounts and RBAC rules
4. **Image Scanning**: Scan container images for vulnerabilities
5. **Audit Logging**: Enable Kubernetes audit logging

## Support

For issues and questions:
- Check application logs
- Review Kubernetes events
- Consult the TAMS API documentation
- Contact the development team 