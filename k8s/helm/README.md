# TAMS API Helm Chart

This Helm chart deploys the TAMS (Time-addressable Media Store) API on Kubernetes, including the API server, UI, and HAProxy S3 proxy.

## Prerequisites

- Kubernetes 1.24+
- Helm 3.0+
- NGINX Ingress Controller (optional, for ingress)
- cert-manager (optional, for TLS certificates)
- Metrics Server (for HPA)

## Installation

### Install the chart

```bash
# Install with default values
helm install tams-api ./k8s/helm

# Install with custom values
helm install tams-api ./k8s/helm -f values-custom.yaml

# Install in a specific namespace
helm install tams-api ./k8s/helm --namespace tams --create-namespace
```

### Install with custom configuration

```bash
helm install tams-api ./k8s/helm \
  --set vast.endpoint="http://your-vast-server:4001" \
  --set vast.bucket="your-bucket" \
  --set s3.endpointUrl="http://tams-api-haproxy-service:80" \
  --set s3.bucketName="your-s3-bucket" \
  --set ingress.hosts[0].host="tams-api.yourdomain.com"
```

## Components

This chart deploys:

1. **TAMS API Server** - Main FastAPI application
2. **TAMS UI** (optional) - React-based web interface
3. **HAProxy** (optional) - S3 proxy for load balancing and presigned URL handling

## Configuration

### Values File

Create a custom `values.yaml` file to override default settings:

```yaml
# Enable/disable components
ui:
  enabled: true
haproxy:
  enabled: true

# VAST Database configuration
vast:
  endpoint: "http://your-vast-server:4001"
  bucket: "your-bucket"
  schema: "tams8"
  accessKey: "your-access-key"
  secretKey: "your-secret-key"

# S3 Storage configuration
# Use HAProxy service if enabled, otherwise direct endpoint
s3:
  endpointUrl: "http://tams-api-haproxy-service:80"  # Use HAProxy
  # endpointUrl: "http://your-s3-server:9000"  # Or direct endpoint
  bucketName: "your-s3-bucket"
  useSsl: false
  rootPath: "/tams8"
  region: "us-east-1"
  accessKeyId: "your-s3-access-key"
  secretAccessKey: "your-s3-secret-key"

# Trino configuration (optional, for dev)
trino:
  enabled: false
  host: "trino-vast"
  port: 8080
  user: "admin"
  catalog: "vast"

# Logging configuration
config:
  logLevel: "INFO"
  logDir: "logs"  # Configurable logs directory

# Persistent volumes
persistence:
  enabled: true
  logs:
    enabled: true
    size: 10Gi
    storageClassName: "standard"
  vastData:
    enabled: true
    size: 50Gi
    storageClassName: "standard"

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
    cpu: 250m
    memory: 256Mi
  limits:
    cpu: 500m
    memory: 512Mi

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
helm install tams-api ./k8s/helm \
  --set secrets.vastAccessKey="your-vast-access-key" \
  --set secrets.vastSecretKey="your-vast-secret-key" \
  --set secrets.s3AccessKeyId="your-s3-access-key" \
  --set secrets.s3SecretAccessKey="your-s3-secret-key" \
  --set secrets.jwtSecret="your-jwt-secret"
```

Or use a secrets file (not recommended for production):

```yaml
# secrets.yaml (DO NOT COMMIT)
secrets:
  vastAccessKey: "your-vast-access-key"
  vastSecretKey: "your-vast-secret-key"
  s3AccessKeyId: "your-s3-access-key"
  s3SecretAccessKey: "your-s3-secret-key"
  jwtSecret: "your-jwt-secret"
```

Then install:
```bash
helm install tams-api ./k8s/helm -f secrets.yaml
```

## Upgrading

```bash
# Upgrade with new values
helm upgrade tams-api ./k8s/helm -f values-custom.yaml

# Upgrade with specific values
helm upgrade tams-api ./k8s/helm \
  --set image.tag="v8.0.1" \
  --set replicaCount=5
```

## Uninstalling

```bash
helm uninstall tams-api
```

**Note**: This will delete all resources including persistent volumes. To keep data, set `persistence.enabled: false` or manually delete PVCs after uninstall.

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

# Test API docs
curl http://localhost:8080/docs
```

### Check logs
```bash
# API logs
kubectl logs -f deployment/tams-api

# UI logs
kubectl logs -f deployment/tams-api-ui

# HAProxy logs
kubectl logs -f deployment/tams-api-haproxy
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
| `image.repository` | API image repository | `tams-api` |
| `image.tag` | API image tag | `latest` |
| `image.pullPolicy` | Image pull policy | `IfNotPresent` |
| `ui.enabled` | Enable UI deployment | `true` |
| `ui.image.repository` | UI image repository | `tams-ui` |
| `ui.image.tag` | UI image tag | `latest` |
| `haproxy.enabled` | Enable HAProxy deployment | `true` |
| `haproxy.image.repository` | HAProxy image repository | `haproxy` |
| `haproxy.image.tag` | HAProxy image tag | `latest` |
| `haproxy.port` | HAProxy service port | `4001` |
| `haproxy.dns` | HAProxy DNS resolver | `10.140.3.248` |
| `haproxy.backendServers` | S3 backend servers | `["172.200.204.1:80", ...]` |

### Service Parameters
| Parameter | Description | Default |
|-----------|-------------|---------|
| `service.type` | API service type | `ClusterIP` |
| `service.port` | API service port | `80` |
| `service.targetPort` | API target port | `8000` |
| `uiService.type` | UI service type | `ClusterIP` |
| `uiService.port` | UI service port | `80` |
| `haproxyService.type` | HAProxy service type | `ClusterIP` |
| `haproxyService.port` | HAProxy service port | `4001` |

### Ingress Parameters
| Parameter | Description | Default |
|-----------|-------------|---------|
| `ingress.enabled` | Enable ingress | `true` |
| `ingress.className` | Ingress class | `nginx` |
| `ingress.hosts` | Ingress hosts | See values.yaml |

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

### Trino Parameters (Optional)
| Parameter | Description | Default |
|-----------|-------------|---------|
| `trino.enabled` | Enable Trino | `false` |
| `trino.host` | Trino host | `trino-vast` |
| `trino.port` | Trino port | `8080` |
| `trino.user` | Trino user | `admin` |
| `trino.catalog` | Trino catalog | `vast` |

### S3 Storage Parameters
| Parameter | Description | Default |
|-----------|-------------|---------|
| `s3.endpointUrl` | S3 endpoint (use HAProxy service if enabled) | `http://tams-api-haproxy-service:80` |
| `s3.bucketName` | S3 bucket | `jthaloor-s3` |
| `s3.useSsl` | Use SSL | `false` |
| `s3.rootPath` | S3 root path | `/tams8` |
| `s3.region` | S3 region | `us-east-1` |

### Logging Parameters
| Parameter | Description | Default |
|-----------|-------------|---------|
| `config.logLevel` | Log level | `INFO` |
| `config.logFormat` | Log format | `%(asctime)s - %(name)s:%(lineno)d - %(levelname)s - %(message)s` |
| `config.logDir` | Logs directory | `logs` |

### Persistence Parameters
| Parameter | Description | Default |
|-----------|-------------|---------|
| `persistence.enabled` | Enable persistence | `true` |
| `persistence.logs.enabled` | Enable logs PVC | `true` |
| `persistence.logs.size` | Logs volume size | `10Gi` |
| `persistence.logs.storageClassName` | Logs storage class | `""` (uses default) |
| `persistence.vastData.enabled` | Enable vast_data PVC | `true` |
| `persistence.vastData.size` | Vast data volume size | `50Gi` |
| `persistence.vastData.storageClassName` | Vast data storage class | `""` (uses default) |

## Troubleshooting

### Common Issues

1. **Pod CrashLoopBackOff**
   - Check logs: `kubectl logs deployment/tams-api`
   - Verify secrets are set correctly
   - Check VAST and S3 connectivity
   - Verify config.yaml is valid: `kubectl get configmap tams-api-config -o jsonpath='{.data.config\.yaml}' | yq`

2. **Ingress not working**
   - Verify NGINX ingress controller is installed
   - Check ingress annotations
   - Verify DNS resolution

3. **HPA not scaling**
   - Check metrics server is installed
   - Verify resource requests/limits are set
   - Check HPA events: `kubectl describe hpa tams-api-hpa`

4. **HAProxy not routing S3 requests**
   - Check HAProxy logs: `kubectl logs deployment/tams-api-haproxy`
   - Verify HAProxy config: `kubectl get configmap tams-api-haproxy-config -o yaml`
   - Check backend servers are accessible

5. **UI not loading**
   - Check UI service is running: `kubectl get svc tams-api-ui-service`
   - Verify UI can reach API: Check network policies
   - Check UI logs: `kubectl logs deployment/tams-api-ui`

### Debug Commands
```bash
# Check all resources
kubectl get all -l app.kubernetes.io/name=tams-api

# Check events
kubectl get events --sort-by='.lastTimestamp'

# Check configmap
kubectl get configmap tams-api-config -o yaml

# Check secrets (base64 encoded)
kubectl get secret tams-api-secrets -o yaml

# Check persistent volumes
kubectl get pvc -l app.kubernetes.io/name=tams-api

# Test service connectivity
kubectl run -it --rm debug --image=curlimages/curl --restart=Never -- curl http://tams-api-service/health
```

## Support

For issues and questions:
- GitHub Issues: https://github.com/jesseVast/vasttams/issues
- Documentation: https://github.com/jesseVast/vasttams
