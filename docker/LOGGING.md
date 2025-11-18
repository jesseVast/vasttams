# Logging in Docker Container

## Overview

TAMS uses a dual logging approach in Docker:
1. **Console logging** (stdout/stderr) - Captured by Docker and accessible via `docker logs`
2. **File logging** - Written to `/app/logs/` inside the container, persisted via Docker volume

## Log Storage

### Container Path
Logs are written to `/app/logs/` inside the container.

### Docker Volume
The log directory is mounted to a persistent Docker volume `logs_data`:

```yaml
volumes:
  - logs_data:/app/logs
```

This ensures logs persist even if the container is recreated.

### Log Files

The application creates the following log files:

1. **`tams.log`** - All application logs (DEBUG and above)
   - Rotating file handler
   - Max size: 10MB per file
   - Backups: 5 files (total ~50MB)
   - Format: Detailed with function names and extra context

2. **`tams_errors.log`** - Error logs only (ERROR level and above)
   - Rotating file handler
   - Max size: 10MB per file
   - Backups: 3 files (total ~30MB)
   - Format: Detailed with function names and extra context

## Accessing Logs

### View Console Logs (stdout/stderr)

```bash
# View all logs
docker logs tams-api

# Follow logs in real-time
docker logs -f tams-api

# View last 100 lines
docker logs --tail 100 tams-api

# View logs with timestamps
docker logs -t tams-api

# View logs from specific time
docker logs --since 2024-01-01T00:00:00 tams-api
```

### Access Log Files

```bash
# View main log file
docker exec -it tams-api tail -f /app/logs/tams.log

# View error log file
docker exec -it tams-api tail -f /app/logs/tams_errors.log

# Copy log files to host
docker cp tams-api:/app/logs/tams.log ./tams.log
docker cp tams-api:/app/logs/tams_errors.log ./tams_errors.log

# List all log files
docker exec -it tams-api ls -lh /app/logs/
```

### Access Volume Directly

The `logs_data` volume can be inspected:

```bash
# Find volume location
docker volume inspect logs_data

# Access volume (requires root or appropriate permissions)
# On Linux, volumes are typically at:
# /var/lib/docker/volumes/<volume_name>/_data
```

## Log Configuration

### Config File Settings

Log directory and level can be configured in `config.yaml`:

```yaml
logging:
  level: "INFO"
  format: "detailed"
  dir: "/app/logs"
```

### Environment Variables

Log settings can be overridden via environment variables:

```bash
# Set log level
TAMS_LOG_LEVEL=DEBUG

# Set log directory (default: /app/logs)
TAMS_LOG_DIR=/custom/log/path
```

### Default Behavior

- **Log directory**: `/app/logs` (created automatically)
- **Log level**: `INFO` (or from config)
- **Console output**: Enabled (INFO level)
- **File output**: Enabled (DEBUG level for tams.log, ERROR for tams_errors.log)

## Log Rotation

Logs are automatically rotated to prevent disk space issues:

- **Rotation trigger**: When file reaches 10MB
- **Backup files**: 
  - `tams.log.1`, `tams.log.2`, etc. (up to 5 backups)
  - `tams_errors.log.1`, `tams_errors.log.2`, etc. (up to 3 backups)
- **Oldest files**: Automatically deleted when backup limit reached

## Log Levels

Available log levels (from least to most verbose):
- `ERROR` - Only errors
- `WARNING` - Warnings and errors
- `INFO` - Informational messages, warnings, and errors (default)
- `DEBUG` - All messages including debug information

## Special Logger Configuration

Some loggers have special handling:

- **`vasts3.client`**: Set to WARNING level to suppress expected 404 errors
- **`app.vaststore`**: Separate logger for VAST store operations
- **`vastdb`**: Separate logger for database operations

## Production Considerations

### Log Aggregation

For production, consider:
- Using a log aggregation service (ELK, Splunk, etc.)
- Configuring Docker logging driver to send logs to external service
- Using `docker-compose` logging driver configuration

Example logging driver configuration:

```yaml
services:
  tams-api:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
    # Or use syslog driver
    # logging:
    #   driver: "syslog"
    #   options:
    #     syslog-address: "tcp://localhost:514"
```

### Disk Space Management

- Log rotation is automatic but monitor disk usage
- Consider setting up log retention policies
- Use external log aggregation to reduce local storage needs
- Monitor the `logs_data` volume size

### Security

- Log files may contain sensitive information
- Ensure proper file permissions (logs are owned by `tamsuser`)
- Consider encrypting log volumes for sensitive deployments
- Review log content before sharing or exporting

## Troubleshooting

### Logs Not Appearing

1. Check container is running: `docker ps`
2. Check log directory exists: `docker exec -it tams-api ls -la /app/logs/`
3. Check permissions: `docker exec -it tams-api ls -la /app/logs/`
4. Check volume mount: `docker inspect tams-api | grep -A 10 Mounts`

### Logs Taking Too Much Space

1. Check current log sizes: `docker exec -it tams-api du -sh /app/logs/*`
2. Reduce log level in config: `"level": "WARNING"`
3. Reduce backup count (requires code change)
4. Set up external log aggregation and reduce retention

### Viewing Specific Log Entries

```bash
# Search for errors
docker logs tams-api 2>&1 | grep ERROR

# Search for specific text
docker exec -it tams-api grep "search term" /app/logs/tams.log

# Count errors
docker exec -it tams-api grep -c ERROR /app/logs/tams_errors.log
```

## Integration with Observability Stack

When running with the `observability` or `full` profile, logs can be:
- Collected by Prometheus (via node-exporter)
- Visualized in Grafana
- Traced in Jaeger (for distributed tracing)

See `docker/README.md` for observability stack setup.

