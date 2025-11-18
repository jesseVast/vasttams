# TAMS API Kubernetes Deployment

**⚠️ IMPORTANT: This project now only supports Helm-based deployments.**

All Kubernetes deployments should use the Helm chart located in `k8s/helm/`. The standalone YAML files in this directory are deprecated and kept for reference only.

## Quick Start

### Using Helm (Recommended)

```bash
# Install TAMS API with Helm
helm install tams-api ./k8s/helm --namespace tams --create-namespace

# Install with custom values
helm install tams-api ./k8s/helm -f custom-values.yaml --namespace tams --create-namespace
```

For complete Helm documentation, see [k8s/helm/README.md](./helm/README.md).

## What's Included

The Helm chart deploys:

1. **TAMS API Server** - Main FastAPI application
2. **TAMS UI** (optional) - React-based web interface  
3. **HAProxy** (optional) - S3 proxy for load balancing and presigned URL handling
4. **Persistent Volumes** - For logs and vast_data
5. **Services** - ClusterIP services for all components
6. **Ingress** - External access with TLS (optional)
7. **HPA** - Horizontal Pod Autoscaler
8. **PDB** - Pod Disruption Budget
9. **Network Policies** - Network isolation (optional)

## Key Features

- **Configurable Logging**: Logs directory configurable via `config.logDir`
- **HAProxy S3 Proxy**: Clients don't talk directly to S3
- **UI Support**: Optional React UI deployment
- **Persistent Storage**: Configurable PVCs for logs and data
- **Full Config Support**: Complete config.yaml structure via ConfigMap
- **Secrets Management**: Secure credential handling
- **Auto-scaling**: HPA based on CPU and memory

## Migration from Standalone YAML

If you were using the standalone YAML files, migrate to Helm:

1. **Extract your configuration** from the old ConfigMap and Secrets
2. **Create a values.yaml** with your settings
3. **Install with Helm**: `helm install tams-api ./k8s/helm -f values.yaml`

The Helm chart provides the same functionality with better configuration management.

## Directory Structure

```
k8s/
├── helm/                    # Helm chart (ONLY supported deployment method)
│   ├── Chart.yaml          # Chart metadata
│   ├── values.yaml         # Default configuration values
│   ├── README.md           # Helm chart documentation
│   └── templates/          # Kubernetes resource templates
│       ├── deployment.yaml # API server deployment
│       ├── ui-deployment.yaml # UI deployment (optional)
│       ├── haproxy-deployment.yaml # HAProxy deployment (optional)
│       ├── service.yaml    # Services for all components
│       ├── configmap.yaml # Application configuration
│       ├── secrets.yaml   # Secrets template
│       ├── ingress.yaml   # Ingress configuration
│       ├── hpa.yaml       # Horizontal Pod Autoscaler
│       ├── pdb.yaml       # Pod Disruption Budget
│       ├── pvc.yaml       # Persistent Volume Claims
│       └── ...
├── README.md               # This file
├── SECURITY_K8S.md         # Security best practices
└── TELEMETRY.md            # Telemetry configuration guide
```

## Documentation

- **Helm Chart README**: [k8s/helm/README.md](./helm/README.md)
- **Security Guide**: [k8s/SECURITY_K8S.md](./SECURITY_K8S.md)
- **Telemetry Guide**: [k8s/TELEMETRY.md](./TELEMETRY.md)

## Support

For issues and questions:
- GitHub Issues: https://github.com/jesseVast/vasttams/issues
- Helm Chart Documentation: [k8s/helm/README.md](./helm/README.md)
