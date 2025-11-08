# TAMS Observability Stack

This directory contains configuration files for the TAMS observability stack, including Prometheus, Grafana, Jaeger, and Alertmanager.

## 📊 Components

- **Prometheus**: Metrics collection and storage
- **Grafana**: Metrics visualization and dashboards
- **Jaeger**: Distributed tracing
- **Alertmanager**: Alert management and routing

## 🚀 Quick Start

### Using Docker Compose

The observability stack is integrated into the main `docker/docker-compose.yml` with the `observability` profile:

```bash
cd docker
# Start observability stack along with TAMS API
docker-compose --profile observability --profile dev up -d

# Or with production stack
docker-compose --profile observability --profile prod up -d
```

### Standalone Observability Stack

To run only the observability stack (without TAMS API):

```bash
cd docker
docker-compose -f docker-compose.observability.yml up -d
```

**Note**: When running standalone, ensure the TAMS API is accessible at `tams-api:8000` or update `observability/prometheus/prometheus.yml` to point to the correct endpoint.

## 📈 Access Points

Once started, access the services at:

- **Grafana Dashboard**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090
- **Jaeger Tracing**: http://localhost:16686
- **Alertmanager**: http://localhost:9093
- **TAMS API Metrics**: http://localhost:8000/metrics
- **TAMS API Health**: http://localhost:8000/health

## ⚙️ Configuration

### Prometheus

Configuration: `prometheus/prometheus.yml`

- Scrapes TAMS API metrics from `tams-api:8000/metrics`
- Collects system metrics from Node Exporter
- Sends alerts to Alertmanager

### Grafana

- **Data Source**: Auto-provisioned from `grafana/provisioning/datasources/prometheus.yml`
- **Dashboards**: Auto-loaded from `grafana/dashboards/`
- **Default Credentials**: admin/admin (change in production!)

### Jaeger

- **Collector Endpoint**: `http://jaeger:14268/api/traces` (HTTP)
- **OTLP Endpoint**: `http://jaeger:4318/v1/traces` (gRPC)
- Configure in TAMS API via `telemetry.jaegerEndpoint` or `telemetry.otlpEndpoint`

### Alertmanager

Configuration: `alertmanager/alertmanager.yml`

- **Webhook Receiver**: Configured in `alertmanager.yml` (update for your needs)
- **Default Route**: Sends all alerts to webhook receiver
- **Inhibition Rules**: Critical alerts suppress warnings

## 🔧 Customization

### Update Prometheus Scrape Targets

Edit `prometheus/prometheus.yml` to add or modify scrape targets:

```yaml
scrape_configs:
  - job_name: 'tams-api'
    static_configs:
      - targets: ['tams-api:8000']  # Use service name in Docker network
```

### Configure Alertmanager Webhooks

Edit `alertmanager/alertmanager.yml` to update webhook receivers:

```yaml
receivers:
  - name: 'web.hook'
    webhook_configs:
      - url: 'http://your-webhook-server:port/webhook'
```

### Add Custom Grafana Dashboards

Place JSON dashboard files in `grafana/dashboards/` - they will be auto-loaded.

## 🐛 Troubleshooting

### Prometheus Can't Scrape TAMS API

1. **Check network connectivity**: Ensure both services are on `tams-network`
2. **Verify service name**: Use `tams-api:8000` (not `localhost:8000`) in Docker network
3. **Check TAMS API health**: `curl http://localhost:8000/health`
4. **Check metrics endpoint**: `curl http://localhost:8000/metrics`

### Grafana Can't Connect to Prometheus

1. **Check Prometheus is running**: `docker ps | grep prometheus`
2. **Verify data source URL**: Should be `http://prometheus:9090` (service name)
3. **Check Grafana logs**: `docker logs tams-grafana`

### Jaeger Not Receiving Traces

1. **Check TAMS API telemetry config**: Verify `jaegerEndpoint` or `otlpEndpoint` is set
2. **Verify Jaeger is running**: `docker ps | grep jaeger`
3. **Check TAMS API logs**: Look for telemetry initialization errors
4. **Test Jaeger endpoint**: `curl http://localhost:14268/api/traces`

## 📚 Related Documentation

- **Kubernetes Deployment**: See `k8s/TELEMETRY.md` for Helm-based observability
- **Application Telemetry**: See `src/server/vasttamsserver/core/telemetry.py`
- **Docker Setup**: See `docker/README.md`

## 🔒 Security Notes

- **Change default Grafana credentials** in production!
- **Restrict network access** to observability services in production
- **Use TLS** for all external-facing endpoints
- **Configure authentication** for Grafana and Prometheus in production

