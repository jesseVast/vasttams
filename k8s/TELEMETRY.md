# TAMS Telemetry Integration with Kubernetes

This document describes how the telemetry features are integrated with the existing Kubernetes deployment.

## 🚀 Quick Start

### Apply Telemetry Updates
```bash
cd k8s
./apply-telemetry.sh
```

### Manual Application
```bash
kubectl apply -f deployment.yaml
kubectl apply -f configmap.yaml
kubectl apply -f service.yaml
kubectl rollout restart deployment tams-api -n tams
```

## 📊 Telemetry Features Enabled

### 1. **Enhanced Health Checks**
- **Endpoint**: `/health`
- **Features**: System metrics, telemetry status, dependency health
- **K8s Integration**: Already configured in liveness/readiness probes

### 2. **Prometheus Metrics**
- **Endpoint**: `/metrics`
- **Features**: HTTP metrics, business metrics, performance metrics
- **K8s Integration**: Service annotations for Prometheus scraping

### 3. **Structured Logging**
- **Features**: Correlation IDs, structured JSON format
- **K8s Integration**: Available in pod logs

### 4. **OpenTelemetry Tracing**
- **Features**: Distributed tracing, correlation IDs
- **K8s Integration**: Environment variables for Jaeger/OTLP endpoints

## 🔧 Configuration Details

### Environment Variables Added
```yaml
env:
- name: TELEMETRY_ENABLED
  value: "true"
- name: METRICS_ENABLED
  value: "true"
- name: TRACING_ENABLED
  value: "true"
- name: JAEGER_ENDPOINT
  value: "jaeger-collector:14268"
- name: OTLP_ENDPOINT
  value: "http://otel-collector:4318/v1/traces"
```

### ConfigMap Updates
```json
{
  "telemetry_enabled": true,
  "metrics_enabled": true,
  "tracing_enabled": true,
  "jaeger_endpoint": "jaeger-collector:14268",
  "otlp_endpoint": "http://otel-collector:4318/v1/traces"
}
```

### Service Annotations
```yaml
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

### System Metrics
- `tams_memory_usage_bytes` - Memory usage
- `tams_active_connections` - Active connections

## 🔍 Verification

### Check Deployment Status
```bash
kubectl get pods -n tams
kubectl logs -f deployment/tams-api -n tams
```

### Test Health Endpoint
```bash
kubectl port-forward service/tams-api-service 8080:80 -n tams
curl http://localhost:8080/health
```

### Test Metrics Endpoint
```bash
kubectl port-forward service/tams-api-service 8080:80 -n tams
curl http://localhost:8080/metrics
```

### Check Service Annotations
```bash
kubectl get service tams-api-service -n tams -o yaml
```

## 🚨 Troubleshooting

### Common Issues

1. **Telemetry not working**
   ```bash
   # Check environment variables
   kubectl exec -it deployment/tams-api -n tams -- env | grep TELEMETRY
   
   # Check logs for telemetry initialization
   kubectl logs deployment/tams-api -n tams | grep telemetry
   ```

2. **Metrics endpoint not accessible**
   ```bash
   # Check service annotations
   kubectl get service tams-api-service -n tams -o yaml
   
   # Test endpoint directly
   kubectl port-forward service/tams-api-service 8080:80 -n tams
   curl http://localhost:8080/metrics
   ```

3. **Health check failures**
   ```bash
   # Check health endpoint
   kubectl port-forward service/tams-api-service 8080:80 -n tams
   curl http://localhost:8080/health
   
   # Check probe configuration
   kubectl get deployment tams-api -n tams -o yaml
   ```

### Debug Commands

```bash
# Check all resources
kubectl get all -n tams

# Check events
kubectl get events -n tams --sort-by='.lastTimestamp'

# Check resource usage
kubectl top pods -n tams

# Check configuration
kubectl get configmap tams-config -n tams -o yaml
```

## 🔄 Updates and Maintenance

### Updating Telemetry Configuration
```bash
# Update configmap
kubectl apply -f configmap.yaml

# Update deployment
kubectl apply -f deployment.yaml

# Restart deployment
kubectl rollout restart deployment tams-api -n tams
```

### Rolling Back Changes
```bash
# Rollback to previous version
kubectl rollout undo deployment tams-api -n tams

# Check rollback status
kubectl rollout status deployment tams-api -n tams
```

## 📝 Next Steps

### Optional: Deploy Full Observability Stack

1. **Prometheus for Metrics Collection**
   ```bash
   # Deploy Prometheus operator
   kubectl apply -f https://raw.githubusercontent.com/prometheus-operator/kube-prometheus/main/manifests/setup/0-namespace.yaml
   kubectl apply -f https://raw.githubusercontent.com/prometheus-operator/kube-prometheus/main/manifests/setup/
   kubectl apply -f https://raw.githubusercontent.com/prometheus-operator/kube-prometheus/main/manifests/
   ```

2. **Grafana for Visualization**
   ```bash
   # Deploy Grafana
   kubectl apply -f https://raw.githubusercontent.com/grafana/helm-charts/main/charts/grafana/templates/deployment.yaml
   ```

3. **Jaeger for Distributed Tracing**
   ```bash
   # Deploy Jaeger
   kubectl apply -f https://raw.githubusercontent.com/jaegertracing/jaeger-kubernetes/main/all-in-one/jaeger-all-in-one-template.yml
   ```

### Service Monitor for Prometheus
```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: tams-api-monitor
  namespace: tams
spec:
  selector:
    matchLabels:
      app: tams-api
  endpoints:
  - port: http
    path: /metrics
    interval: 15s
```

## 📞 Support

For issues with telemetry integration:
1. Check the troubleshooting section
2. Review pod logs for telemetry initialization
3. Verify environment variables are set correctly
4. Test endpoints directly with port-forward
5. Check service annotations for Prometheus scraping 