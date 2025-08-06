# TAMS Observability Stack

This document describes the comprehensive observability and telemetry features implemented in the TAMS API.

## 🚀 Quick Start

### Start the Observability Stack
```bash
./start-observability.sh
```

### Access Points
- **Grafana Dashboard**: http://localhost:3000
  - **Username:** admin
  - **Password:** admin
- **Prometheus**: http://localhost:9090
- **Jaeger Tracing**: http://localhost:16686
- **Alertmanager**: http://localhost:9093
- **TAMS Metrics**: http://localhost:8000/metrics
- **TAMS Health**: http://localhost:8000/health

## 📊 Telemetry Features

### 1. Prometheus Metrics

The TAMS API exposes comprehensive Prometheus metrics at `/metrics`:

#### HTTP Metrics
- `tams_http_requests_total` - Total HTTP requests by method, endpoint, and status code
- `tams_http_request_duration_seconds` - Request duration histograms
- `tams_errors_total` - Error counts by type and endpoint

#### Business Metrics
- `tams_sources_total` - Total number of sources
- `tams_flows_total` - Total number of flows
- `tams_segments_total` - Total number of flow segments
- `tams_storage_bytes_total` - Total storage usage in bytes

#### Operation Metrics
- `tams_flow_operations_total` - Flow operations by type, format, and status
- `tams_segment_operations_total` - Segment operations by type and status
- `tams_source_operations_total` - Source operations by type, format, and status

#### Performance Metrics
- `tams_vast_query_duration_seconds` - VAST database query performance
- `tams_s3_operation_duration_seconds` - S3 operation performance

#### System Metrics
- `tams_memory_usage_bytes` - Memory usage
- `tams_active_connections` - Active database connections

### 2. OpenTelemetry Tracing

Distributed tracing is implemented using OpenTelemetry:

#### Trace Features
- Automatic instrumentation of FastAPI endpoints
- Custom spans for business operations
- Correlation IDs for request tracking
- Integration with Jaeger for trace visualization

#### Trace Decorators
```python
from app.telemetry import trace_operation

@trace_operation("flow_creation")
async def create_flow(flow_data):
    # Operation will be traced automatically
    pass
```

### 3. Enhanced Logging

- Structured logging with correlation IDs
- Configurable log levels and formats
- Integration with OpenTelemetry logging instrumentation

### 4. Health Checks

Enhanced health check endpoint at `/health` includes:
- Application status
- System metrics (CPU, memory, uptime)
- Telemetry status
- Version information

## 🏗️ Architecture

### Components

1. **TAMS API** - Main application with embedded telemetry
2. **Prometheus** - Metrics collection and storage
3. **Grafana** - Metrics visualization and dashboards
4. **Jaeger** - Distributed tracing visualization
5. **Alertmanager** - Alert management and routing
6. **Node Exporter** - System metrics collection

### Data Flow

```
TAMS API → Prometheus Metrics → Grafana Dashboards
     ↓
Jaeger Tracing → Trace Visualization
     ↓
Alertmanager → Alert Notifications
```

## 📈 Dashboards

### TAMS Overview Dashboard

The main dashboard includes:

1. **HTTP Request Rate** - Request rate by endpoint and method
2. **HTTP Request Duration** - 95th and 50th percentile response times
3. **Error Rate** - Error rates by type and endpoint
4. **Business Metrics** - Sources, flows, segments, and storage counts
5. **VAST Query Performance** - Database query performance
6. **S3 Operation Performance** - Storage operation performance
7. **System Resources** - Memory and CPU usage
8. **Operation Counts** - Business operation rates

### Custom Dashboards

You can create additional dashboards for:
- **Flow Analytics** - Flow-specific metrics and trends
- **Storage Analytics** - Storage usage patterns and optimization
- **Error Analysis** - Error patterns and debugging
- **Performance Monitoring** - System performance trends

## 🔐 Authentication & Security

### Default Credentials

The observability stack uses the following default credentials:

#### Grafana
- **URL:** http://localhost:3000
- **Username:** admin
- **Password:** admin

#### Other Services
- **Prometheus:** No authentication required
- **Jaeger:** No authentication required  
- **Alertmanager:** No authentication required
- **TAMS API:** No authentication required

### Security Considerations

⚠️ **Important:** The default credentials (`admin/admin`) are suitable for development and testing environments only. For production deployments:

1. **Change default passwords** - Update Grafana admin password
2. **Use environment variables** - Set credentials via environment variables
3. **Implement additional security** - Consider reverse proxy authentication
4. **Network security** - Restrict access to observability endpoints
5. **Regular credential rotation** - Implement password rotation policies

### Production Security Setup

For production environments, modify the docker-compose configuration:

```yaml
grafana:
  environment:
    - GF_SECURITY_ADMIN_USER=${GRAFANA_ADMIN_USER}
    - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_ADMIN_PASSWORD}
    - GF_USERS_ALLOW_SIGN_UP=false
    - GF_AUTH_ANONYMOUS_ENABLED=false
```

## 🔧 Configuration

```bash
# Jaeger Configuration (Optional)
JAEGER_ENDPOINT=localhost:14268

# OTLP Configuration (Optional)
OTLP_ENDPOINT=http://localhost:4318/v1/traces
```

**Note**: Telemetry is enabled by default and cannot be disabled through configuration.

### Prometheus Configuration

The Prometheus configuration (`observability/prometheus/prometheus.yml`) includes:
- TAMS API metrics scraping
- System metrics collection
- Alert rules and routing

### Grafana Configuration

Grafana is pre-configured with:
- Prometheus datasource
- TAMS overview dashboard
- Auto-provisioning of dashboards

## 🚨 Alerting

### Alert Rules

Prometheus alert rules can be configured for:
- High error rates
- Slow response times
- System resource usage
- Business metric thresholds

### Alert Channels

Alertmanager supports multiple notification channels:
- Email
- Slack
- PagerDuty
- Webhooks

## 🔍 Troubleshooting

### Common Issues

1. **Metrics not appearing**
   - Check if TAMS API is running on port 8000
   - Verify `/metrics` endpoint is accessible
   - Check Prometheus target status

2. **Tracing not working**
   - Verify Jaeger is running on port 16686
   - Check JAEGER_ENDPOINT configuration
   - Ensure OpenTelemetry is properly initialized

3. **Dashboard not loading**
   - Check Grafana is running on port 3000
   - Verify Prometheus datasource is configured
   - Check dashboard JSON syntax

### Debug Commands

```bash
# Check service status
docker-compose -f docker-compose.observability.yml ps

# View logs
docker-compose -f docker-compose.observability.yml logs prometheus
docker-compose -f docker-compose.observability.yml logs grafana
docker-compose -f docker-compose.observability.yml logs jaeger

# Test metrics endpoint
curl http://localhost:8000/metrics

# Test health endpoint
curl http://localhost:8000/health
```

## 📚 Integration Examples

### Adding Custom Metrics

```python
from app.telemetry import metrics

# Record custom business metric
metrics.custom_metric.inc()

# Record custom histogram
metrics.custom_duration.observe(duration)
```

### Adding Custom Traces

```python
from app.telemetry import telemetry_manager

tracer = telemetry_manager.get_tracer()
with tracer.start_as_current_span("custom_operation") as span:
    span.set_attribute("custom.attribute", "value")
    # Your operation here
```

### Adding Custom Logs

```python
import logging
from app.telemetry import telemetry_manager

logger = logging.getLogger(__name__)
logger.info("Custom log message", extra={
    "correlation_id": request.state.correlation_id,
    "custom_field": "value"
})
```

## 🔄 Updates and Maintenance

### Updating Dependencies

```bash
# Update telemetry dependencies
pip install -r requirements.txt

# Update observability stack
docker-compose -f docker-compose.observability.yml pull
docker-compose -f docker-compose.observability.yml up -d
```

### Backup and Restore

```bash
# Backup Prometheus data
docker run --rm -v tams_prometheus_data:/data -v $(pwd):/backup alpine tar czf /backup/prometheus-backup.tar.gz -C /data .

# Backup Grafana data
docker run --rm -v tams_grafana_data:/data -v $(pwd):/backup alpine tar czf /backup/grafana-backup.tar.gz -C /data .
```

## 📞 Support

For issues with the observability stack:
1. Check the troubleshooting section
2. Review service logs
3. Verify configuration files
4. Test individual components
5. Check network connectivity between services 