# Configuration File Documentation

This document describes the `config.json` configuration file used by the TAMS (Time-addressable Media Store) server.

## Configuration File Location

The server looks for the configuration file in the following order:
1. `/etc/tams/config.json` (production - mounted config)
2. `config/config.json` (development - local config)

If neither file exists, the server will use default values for all settings.

## Configuration Sections

### API Configuration

```json
{
  "api": {
    "title": "TAMS API",
    "version": "8.0",
    "description": "Time-addressable Media Store API"
  }
}
```

- **`title`** (string): API title displayed in OpenAPI documentation
- **`version`** (string): API version (e.g., "8.0")
- **`description`** (string): API description displayed in OpenAPI documentation

### Server Configuration

```json
{
  "server": {
    "host": "0.0.0.0",
    "port": 8000,
    "debug": false,
    "workers": 1
  }
}
```

- **`host`** (string): Server bind address. Use `0.0.0.0` to listen on all interfaces, or a specific IP address
- **`port`** (integer): Server port number (default: 8000)
- **`debug`** (boolean): Enable debug mode. **Should be `false` in production** for security and performance
- **`workers`** (integer): Number of uvicorn worker processes. Set to `1` for single-process mode (useful for development), or higher for production (default: 4)

### Database Configuration

```json
{
  "database": {
    "vast": {
      "endpoint": "http://docker1:4001",
      "access_key": "SRSPW0DQT9T70Y787U68",
      "secret_key": "WkKLxvG7YkAdSMuHjFsZG5/BhDk9Ou7BS1mDQGnr",
      "bucket": "jthaloor-db",
      "schema": "tams8-dev"
    },
    "trino": {
      "host": "docker1",
      "port": 8080,
      "user": "admin",
      "catalog": "vast",
      "enabled": true
    },
    "enable_table_projections": true
  }
}
```

#### VAST Database Settings

- **`endpoint`** (string): VAST database endpoint URL
- **`access_key`** (string): VAST database access key
- **`secret_key`** (string): VAST database secret key
- **`bucket`** (string): VAST database bucket name
- **`schema`** (string): VAST database schema name

#### Trino Settings

- **`host`** (string): Trino server hostname or IP address
- **`port`** (integer): Trino server port (default: 8080)
- **`user`** (string): Trino username
- **`catalog`** (string): Trino catalog name (typically "vast")
- **`enabled`** (boolean): Enable Trino integration for SQL capabilities

#### Table Projections

- **`enable_table_projections`** (boolean): Enable table projections for improved query performance. Creates projections for:
  - `source(id)`
  - `flow(id)`
  - `segment(id, flow_id, object_id)`
  - `object(id)`
  - `flow_object_references(id)`

### Storage Backends Configuration

```json
{
  "storage_backends": [
    {
      "id": "default",
      "label": "default-s3-storage",
      "store_type": "http_object_store",
      "provider": "vast",
      "store_product": "vast-s3",
      "region": "us-east-1",
      "availability_zone": null,
      "endpoint_url": "http://docker1:4001",
      "access_key": "SRSPW0DQT9T70Y787U68",
      "secret_key": "WkKLxvG7YkAdSMuHjFsZG5/BhDk9Ou7BS1mDQGnr",
      "bucket_name": "jthaloor-s3",
      "root_path": "/tams8-dev",
      "use_ssl": false,
      "chunk_size": 8388608,
      "max_concurrent_parts": 10,
      "default_storage": true
    }
  ]
}
```

Multiple storage backends can be configured. Each backend supports:

- **`id`** (string, required): Unique identifier for the storage backend
- **`label`** (string): Human-readable label for the storage backend
- **`store_type`** (string): Storage type (e.g., `"http_object_store"`)
- **`provider`** (string): Storage provider (e.g., `"vast"`, `"minio"`, `"aws"`)
- **`store_product`** (string): Product identifier (e.g., `"vast-s3"`, `"minio"`)
- **`region`** (string): AWS region (use `"us-east-1"` for custom endpoints)
- **`availability_zone`** (string|null): Availability zone (optional)
- **`endpoint_url`** (string): S3-compatible storage endpoint URL
- **`access_key`** (string): S3 access key ID
- **`secret_key`** (string): S3 secret access key
- **`bucket_name`** (string): S3 bucket name for media storage
- **`root_path`** (string): Root path prefix for all objects (e.g., `"/tams8-dev"`)
- **`use_ssl`** (boolean): Enable SSL/TLS for S3 connections
- **`chunk_size`** (integer): Multipart upload chunk size in bytes (default: 8388608 = 8MB)
- **`max_concurrent_parts`** (integer): Maximum concurrent parts for multipart uploads (default: 10)
- **`default_storage`** (boolean): Mark this backend as the default storage backend

### Storage Configuration

```json
{
  "storage": {
    "default_backend_id": "default",
    "tams_storage_path": "tams",
    "tams_root": "/tams",
    "presigned_url": {
      "upload_timeout": 3600,
      "download_timeout": 3600
    },
    "get_urls_max_count": 5,
    "flow_storage_default_limit": 10,
    "segment_storage_default_limit": 10,
    "async_deletion_threshold": 1000
  }
}
```

- **`default_backend_id`** (string): ID of the default storage backend (must match an ID in `storage_backends`)
- **`tams_storage_path`** (string): Base path for TAMS media storage organization
- **`tams_root`** (string): S3 TAMS root path for legacy compatibility
- **`presigned_url.upload_timeout`** (integer): Presigned URL timeout for upload operations in seconds (default: 3600 = 1 hour)
- **`presigned_url.download_timeout`** (integer): Presigned URL timeout for download operations in seconds (default: 3600 = 1 hour)
- **`get_urls_max_count`** (integer): Maximum number of get_urls to generate per segment (default: 5)
- **`flow_storage_default_limit`** (integer): Default limit for flow storage allocation when no limit is specified (default: 10)
- **`segment_storage_default_limit`** (integer): Default limit for segment storage allocation when no limit is specified (default: 10)
- **`async_deletion_threshold`** (integer): Threshold for triggering async deletion workflow (number of segments, default: 1000)

### Logging Configuration

```json
{
  "logging": {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s:%(lineno)d - %(levelname)s - %(message)s",
    "dir": "logs"
  }
}
```

- **`level`** (string): Log level (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`). Use `INFO` for production, `DEBUG` for development
- **`format`** (string): Log message format string using Python logging format specifiers
- **`dir`** (string): Directory path for log files (relative to working directory or absolute path). Log files are written to this directory.

### TAMS Compliance Configuration

```json
{
  "tams_compliance": {
    "enabled": true,
    "validation_level": "strict",
    "uuid_validation": true,
    "timestamp_validation": true,
    "content_format_validation": true,
    "mime_type_validation": true,
    "error_reporting": true,
    "audit_logging": true,
    "cache_enabled": true,
    "cache_ttl": 300
  }
}
```

- **`enabled`** (boolean): Enable TAMS API compliance mode
- **`validation_level`** (string): Validation level - `"strict"`, `"relaxed"`, or `"minimal"`
- **`uuid_validation`** (boolean): Enable strict UUID validation according to TAMS specification
- **`timestamp_validation`** (boolean): Enable strict timestamp validation according to TAMS specification
- **`content_format_validation`** (boolean): Enable strict content format URN validation
- **`mime_type_validation`** (boolean): Enable strict MIME type validation
- **`error_reporting`** (boolean): Enable TAMS-specific error reporting and logging
- **`audit_logging`** (boolean): Enable TAMS compliance audit logging
- **`cache_enabled`** (boolean): Enable TAMS-specific caching for improved performance
- **`cache_ttl`** (integer): TAMS cache TTL in seconds (default: 300, max: 86400 = 24 hours)

### Telemetry Configuration

```json
{
  "telemetry": {
    "enabled": true,
    "metrics_enabled": true,
    "tracing_enabled": true,
    "jaeger_endpoint": "localhost:14268",
    "otlp_endpoint": "http://localhost:4318/v1/traces"
  }
}
```

- **`enabled`** (boolean): Enable telemetry collection
- **`metrics_enabled`** (boolean): Enable metrics collection
- **`tracing_enabled`** (boolean): Enable distributed tracing
- **`jaeger_endpoint`** (string): Jaeger endpoint for trace export (format: `host:port`)
- **`otlp_endpoint`** (string): OTLP endpoint for trace export (URL format)

### Authentication Configuration

```json
{
  "authentication": {
    "secret_key": "your-secret-key-here-change-in-production",
    "algorithm": "HS256",
    "access_token_expire_minutes": 30
  }
}
```

- **`secret_key`** (string): **IMPORTANT**: Secret key for JWT token generation. **Must be changed in production** to a secure random string
- **`algorithm`** (string): JWT algorithm for token generation (default: `"HS256"`)
- **`access_token_expire_minutes`** (integer): JWT access token expiration time in minutes (default: 30)

### Webhooks Configuration

```json
{
  "webhooks": {
    "timeout": 30,
    "retry_attempts": 3
  }
}
```

- **`timeout`** (integer): Webhook request timeout in seconds (default: 30)
- **`retry_attempts`** (integer): Number of retry attempts for failed webhooks (default: 3)

### Redis Configuration

```json
{
  "redis": {
    "enabled": true,
    "host": "localhost",
    "port": 6379,
    "password": "redis",
    "db": 0,
    "ssl": false,
    "socket_timeout": 5,
    "socket_connect_timeout": 5,
    "max_connections": 50,
    "health_check_interval": 30
  }
}
```

- **`enabled`** (boolean): Enable Redis caching (required for multi-container deployments)
- **`host`** (string): Redis server hostname or IP address
- **`port`** (integer): Redis server port (default: 6379)
- **`password`** (string|null): Redis password (if required, set to `null` if no password)
- **`db`** (integer): Redis database number (0-15, default: 0)
- **`ssl`** (boolean): Enable SSL/TLS for Redis connections
- **`socket_timeout`** (integer): Redis socket timeout in seconds (default: 5)
- **`socket_connect_timeout`** (integer): Redis socket connection timeout in seconds (default: 5)
- **`max_connections`** (integer): Maximum number of Redis connections in the pool (default: 50)
- **`health_check_interval`** (integer): Redis health check interval in seconds (default: 30)

## Environment Variables

All configuration values can also be set via environment variables using the `TAMS_` prefix. For example:

- `TAMS_HOST` → `server.host`
- `TAMS_PORT` → `server.port`
- `TAMS_VAST_ENDPOINT` → `database.vast.endpoint`
- `TAMS_REDIS_HOST` → `redis.host`

Environment variables take precedence over values in `config.json`.

## Production Considerations

1. **Security**:
   - Change `authentication.secret_key` to a secure random string
   - Set `server.debug` to `false`
   - Use strong passwords for database and storage credentials
   - Consider using environment variables for sensitive values instead of storing them in the config file

2. **Performance**:
   - Set `server.workers` to match your CPU cores (typically 4-8)
   - Enable `database.enable_table_projections` for better query performance
   - Configure `redis.enabled: true` for multi-container deployments
   - Adjust `storage.chunk_size` and `storage.max_concurrent_parts` based on your network and storage performance

3. **Monitoring**:
   - Enable telemetry for production monitoring
   - Configure appropriate log levels (`INFO` for production, `DEBUG` only for troubleshooting)
   - Set up log rotation for the logs directory

4. **Storage**:
   - Ensure `storage.default_backend_id` matches a valid backend ID
   - Configure appropriate timeouts for presigned URLs based on your use case
   - Set `async_deletion_threshold` based on your deletion patterns

## Example Configuration

See `config/config.json` for a complete example configuration file.

