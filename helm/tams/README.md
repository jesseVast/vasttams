# TAMS API Helm Chart

This Helm chart deploys the TAMS (Time-addressable Media Store) API on Kubernetes.

## Prerequisites

- Kubernetes 1.24+
- Helm 3.0+
- NGINX Ingress Controller
- cert-manager (for TLS certificates)
- Metrics Server (for HPA)

## Installation

### Add the Helm repository (if using a repository)
```bash
helm repo add tams https://your-helm-repo.com
helm repo update
```

### Install the chart
```bash
# Install with default values
helm install tams-api ./helm/tams

# Install with custom values
helm install tams-api ./helm/tams -f values-custom.yaml

# Install in a specific namespace
helm install tams-api ./helm/tams --namespace tams --create-namespace
```

### Install with custom configuration
```bash
helm install tams-api ./helm/tams \
  --set vast.endpoint="http://your-vast-server:8080" \
  --set vast.bucket="your-bucket" \
  --set s3.endpointUrl="http://your-s3-server:9000" \
  --set s3.bucketName="your-s3-bucket" \
  --set ingress.hosts[0].host="tams-api.yourdomain.com"
```

## Configuration

### Values File
Create a custom `values.yaml` file to override default settings:

```yaml
# VAST Database configuration
vast:
  endpoint: "http://your-vast-server:8080"
  bucket: "your-bucket"
  schema: "tams-schema"
  accessKey: "your-access-key"
  secretKey: "your-secret-key"

# S3 Storage configuration
s3:
  endpointUrl: "http://your-s3-server:9000"
  bucketName: "your-s3-bucket"
  useSsl: false
  accessKeyId: "your-s3-access-key"
  secretAccessKey: "your-s3-secret-key"

# Ingress configuration
ingress:
  enabled: true
  hosts:
    - host: tams-api.yourdomain.com
      paths:
        - path: /
          pathType: Prefix

# Resource limits
resources:
  requests:
    cpu: 500m
    memory: 512Mi
  limits:
    cpu: 1000m
    memory: 1Gi

# Scaling configuration
replicaCount: 3
hpa:
  enabled: true
  minReplicas: 2
  maxReplicas: 10
```

### Secrets Management
For production deployments, set the secrets values:

```bash
helm install tams-api ./helm/tams \
  --set secrets.vastAccessKey="your-vast-access-key" \
  --set secrets.vastSecretKey="your-vast-secret-key" \
  --set secrets.s3AccessKeyId="your-s3-access-key" \
  --set secrets.s3SecretAccessKey="your-s3-secret-key"
```

## Upgrading

```bash
# Upgrade with new values
helm upgrade tams-api ./helm/tams -f values-custom.yaml

# Upgrade with specific values
helm upgrade tams-api ./helm/tams \
  --set image.tag="v1.1.0" \
  --set replicaCount=5
```

## Uninstalling

```bash
helm uninstall tams-api
```

## Verification

### Check deployment status
```bash
kubectl get pods -l app.kubernetes.io/name=tams-api
kubectl get services -l app.kubernetes.io/name=tams-api
kubectl get ingress -l app.kubernetes.io/name=tams-api
```

### Test the API
```bash
# Port forward to test locally
kubectl port-forward service/tams-api-service 8080:80

# Test health endpoint
curl http://localhost:8080/health

# Test analytics endpoint
curl http://localhost:8080/analytics/flow-usage
```

### Check logs
```bash
kubectl logs -f deployment/tams-api
```

## Configuration Parameters

### Global Parameters
| Parameter | Description | Default |
|-----------|-------------|---------|
| `global.environment` | Environment name | `production` |
| `global.imageRegistry` | Global image registry | `""` |

### Image Parameters
| Parameter | Description | Default |
|-----------|-------------|---------|
| `image.repository` | Image repository | `tams-api` |
| `image.tag` | Image tag | `latest` |
| `image.pullPolicy` | Image pull policy | `IfNotPresent` |

### Service Parameters
| Parameter | Description | Default |
|-----------|-------------|---------|
| `service.type` | Service type | `ClusterIP` |
| `service.port` | Service port | `80` |
| `service.targetPort` | Target port | `8000` |

### Ingress Parameters
| Parameter | Description | Default |
|-----------|-------------|---------|
| `ingress.enabled` | Enable ingress | `true` |
| `ingress.className` | Ingress class | `nginx` |
| `ingress.hosts` | Ingress hosts | `[{"host": "tams-api.example.com", "paths": [{"path": "/", "pathType": "Prefix"}]}]` |

### HPA Parameters
| Parameter | Description | Default |
|-----------|-------------|---------|
| `hpa.enabled` | Enable HPA | `true` |
| `hpa.minReplicas` | Minimum replicas | `2` |
| `hpa.maxReplicas` | Maximum replicas | `10` |
| `hpa.targetCPUUtilizationPercentage` | CPU target | `70` |
| `hpa.targetMemoryUtilizationPercentage` | Memory target | `80` |

### VAST Database Parameters
| Parameter | Description | Default |
|-----------|-------------|---------|
| `vast.endpoint` | VAST endpoint | `http://172.200.204.1` |
| `vast.bucket` | VAST bucket | `jthaloor-db` |
| `vast.schema` | VAST schema | `bbctams` |

### S3 Storage Parameters
| Parameter | Description | Default |
|-----------|-------------|---------|
| `s3.endpointUrl` | S3 endpoint | `http://172.200.204.1` |
| `s3.bucketName` | S3 bucket | `jthaloor-s3` |
| `s3.useSsl` | Use SSL | `false` |

## Troubleshooting

### Common Issues

1. **Pod CrashLoopBackOff**
   - Check logs: `kubectl logs deployment/tams-api`
   - Verify secrets are set correctly
   - Check VAST and S3 connectivity

2. **Ingress not working**
   - Verify NGINX ingress controller is installed
   - Check ingress annotations
   - Verify DNS resolution

3. **HPA not scaling**
   - Check metrics server is installed
   - Verify resource requests/limits are set
   - Check HPA events: `kubectl describe hpa tams-api-hpa`

### Debug Commands
```bash
# Check all resources
kubectl get all -l app.kubernetes.io/name=tams-api

# Check events
kubectl get events --sort-by='.lastTimestamp'

# Check configmap
kubectl get configmap tams-api-config -o yaml

# Check secrets
kubectl get secret tams-api-secrets -o yaml
```

## Support

For issues and questions:
- GitHub Issues: https://github.com/jesseVast/bbctams/issues
- Documentation: https://github.com/jesseVast/bbctams 