# TAMS Telemetry Integration with Kubernetes

This document describes how telemetry features are configured in the Helm chart deployment.

## 🚀 Quick Start

### Using Helm

Telemetry is configured through Helm values:

```bash
# Install with telemetry enabled (default)
helm install tams-api ./k8s/helm \
  --set telemetry.enabled=true \
  --set telemetry.metricsEnabled=true \
  --set telemetry.tracingEnabled=true \
  --set telemetry.jaegerEndpoint="jaeger-collector:14268" \
  --set telemetry.otlpEndpoint="http://otel-collector:4318/v1/traces"
```

Or configure in `values.yaml`:

```yaml
telemetry:
  enabled: true
  metricsEnabled: true
  tracingEnabled: true
  jaegerEndpoint: "jaeger-collector:14268"
  otlpEndpoint: "http://otel-collector:4318/v1/traces"
```

## 📊 Telemetry Features

### 1. **Enhanced Health Checks**
- **Endpoint**: `/health`
- **Features**: System metrics, telemetry status, dependency health
- **K8s Integration**: Configured in liveness/readiness probes via Helm values

### 2. **Prometheus Metrics**
- **Endpoint**: `/metrics`
- **Features**: HTTP metrics, business metrics, performance metrics
- **K8s Integration**: Service annotations can be added via `service.annotations` in values.yaml

### 3. **Structured Logging**
- **Features**: Correlation IDs, structured JSON format
- **K8s Integration**: Available in pod logs
- **Configurable**: Log directory via `config.logDir` in values.yaml

### 4. **OpenTelemetry Tracing**
- **Features**: Distributed tracing, correlation IDs
- **K8s Integration**: Environment variables configured via Helm values

## 🔧 Configuration

### Helm Values

Telemetry is configured in the Helm chart's `values.yaml`:

```yaml
telemetry:
  enabled: true
  metricsEnabled: true
  tracingEnabled: true
  jaegerEndpoint: ""  # Optional: Jaeger collector endpoint
  otlpEndpoint: ""    # Optional: OTLP collector endpoint
```

### Service Annotations for Prometheus

To enable Prometheus scraping, add annotations to the service:

```yaml
service:
  annotations:
    prometheus.io/scrape: "true"
    prometheus.io/path: "/metrics"
    prometheus.io/port: "8000"
```

## 📈 Available Metrics

### HTTP Metrics
- `tams_http_requests_total` - Request counts by method, endpoint, status
- `tams_http_request_duration_seconds` - Request duration histograms
- `tams_errors_total` - Error counts by type and endpoint

### Business Metrics
- `tams_sources_total` - Total number of sources
- `tams_flows_total` - Total number of flows
- `tams_segments_total` - Total number of segments
- `tams_storage_bytes_total` - Total storage usage

### Performance Metrics
- `tams_vast_query_duration_seconds` - VAST database performance
- `tams_s3_operation_duration_seconds` - S3 operation performance
- `tams_list_query_duration_seconds` - List operation query duration
- `tams_list_json_parse_duration_seconds` - JSON parsing duration
- `tams_list_processing_duration_seconds` - Total list processing time
- `tams_list_record_count` - Number of records in list operations

### System Metrics
- `tams_memory_usage_bytes` - Memory usage
- `tams_active_connections` - Active connections

## 🔍 Verification

### Check Deployment Status
```bash
kubectl get pods -l app.kubernetes.io/name=tams-api
kubectl logs -f deployment/tams-api
```

### Test Health Endpoint
```bash
kubectl port-forward service/tams-api-service 8080:80
curl http://localhost:8080/health
```

### Test Metrics Endpoint
```bash
kubectl port-forward service/tams-api-service 8080:80
curl http://localhost:8080/metrics
```

### Check Configuration
```bash
# Check configmap
kubectl get configmap tams-api-config -o jsonpath='{.data.config\.json}' | jq .telemetry

# Check environment variables
kubectl exec -it deployment/tams-api -- env | grep TELEMETRY
```

## 🚨 Troubleshooting

### Common Issues

1. **Telemetry not working**
   ```bash
   # Check environment variables
   kubectl exec -it deployment/tams-api -- env | grep TELEMETRY
   
   # Check logs for telemetry initialization
   kubectl logs deployment/tams-api | grep telemetry
   ```

2. **Metrics endpoint not accessible**
   ```bash
   # Check service annotations
   kubectl get service tams-api-service -o yaml
   
   # Test endpoint directly
   kubectl port-forward service/tams-api-service 8080:80
   curl http://localhost:8080/metrics
   ```

3. **Health check failures**
   ```bash
   # Check health endpoint
   kubectl port-forward service/tams-api-service 8080:80
   curl http://localhost:8080/health
   
   # Check probe configuration
   kubectl get deployment tams-api -o yaml
   ```

## 🔄 Updates and Maintenance

### Updating Telemetry Configuration

```bash
# Update via Helm
helm upgrade tams-api ./k8s/helm \
  --set telemetry.jaegerEndpoint="new-jaeger-endpoint:14268" \
  --reuse-values

# Or update values.yaml and upgrade
helm upgrade tams-api ./k8s/helm -f values.yaml
```

### Rolling Back Changes

```bash
# Rollback to previous version
helm rollback tams-api

# Check rollback status
helm history tams-api
```

## 📝 Next Steps

### Optional: Deploy Full Observability Stack

1. **Prometheus for Metrics Collection**
   ```bash
   # Using Helm
   helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
   helm install prometheus prometheus-community/kube-prometheus-stack
   ```

2. **Grafana for Visualization**
   ```bash
   # Included with kube-prometheus-stack
   # Access at: kubectl port-forward svc/prometheus-grafana 3000:80
   ```

3. **Jaeger for Distributed Tracing**
   ```bash
   # Using Helm
   helm repo add jaegertracing https://jaegertracing.github.io/helm-charts
   helm install jaeger jaegertracing/jaeger
   ```

### Service Monitor for Prometheus

Create a ServiceMonitor resource (if using Prometheus Operator):

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: tams-api-monitor
  namespace: tams
spec:
  selector:
    matchLabels:
      app.kubernetes.io/name: tams-api
  endpoints:
  - port: http
    path: /metrics
    interval: 15s
```

## 📞 Support

For issues with telemetry integration:
1. Check the troubleshooting section
2. Review pod logs for telemetry initialization
3. Verify Helm values are set correctly
4. Test endpoints directly with port-forward
5. Check service annotations for Prometheus scraping
