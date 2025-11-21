# TAMS Docker Setup

This directory contains Docker configuration files for running TAMS in containerized environments.

## Directory Structure

- `server/` - Server-related Docker files
  - `Dockerfile` - Server container image
  - `config/` - Configuration examples (production.yaml.example)
  - `haproxy/` - HAProxy configuration for S3 proxying
  - `trino/` - Trino configuration files
  - `BUILD.md` - Server build documentation
  - `LOGGING.md` - Logging configuration documentation
- `ui/` - UI-related Docker files
  - `Dockerfile.ui` - UI container image
  - `nginx.conf` - Nginx configuration for UI
- `docker-compose.yml` - Multi-container orchestration (includes Redis, Trino, HAProxy, observability)
- `docker-compose.simple.yml` - Minimal setup (UI and server only)
- `docker-compose.observability.yml` - Observability stack configuration

## Quick Start

### Simple Mode (UI and Server Only)

```bash
cd docker
docker-compose -f docker-compose.simple.yml up
```

### Development Mode

```bash
cd docker
docker-compose up
```

### Production Mode

```bash
cd docker
docker-compose --profile prod up
```

### Full Stack (with observability)

```bash
cd docker
docker-compose --profile full up
```

## Management Scripts in Container

All management scripts from the `mgmt/` directory are available inside the container at `/app/mgmt/`.

### Running Management Scripts

To run management scripts inside the container:

```bash
# Execute a script in the running container
docker exec -it tams-api python /app/mgmt/user_mgmt.py list

# Initialize default users
docker exec -it tams-api python /app/mgmt/user_mgmt.py init-default-users

# Query tables
docker exec -it tams-api python /app/mgmt/query_tables.py --list-tables

# Cleanup database (with confirmation)
docker exec -it tams-api python /app/mgmt/cleanup_database.py

# Delete sources by label filter
docker exec -it tams-api python /app/mgmt/delete_sources_by_label_filter.py "Test"

# Get database version
docker exec -it tams-api python /app/mgmt/get_db_version.py

# Generate OpenAPI spec
docker exec -it tams-api python /app/mgmt/generate_openapi.py
```

### Available Scripts

- `user_mgmt.py` - User management (create, delete, update users and roles)
- `query_tables.py` - Query and export table data
- `cleanup_database.py` - Delete all tables (use with caution!)
- `delete_sources_by_label_filter.py` - Delete sources by label prefix
- `get_db_version.py` - Get database version information
- `create_table_projections.py` - Show projection status (deprecated)
- `generate_openapi.py` - Generate OpenAPI specification

### Configuration

Scripts use the same configuration as the server:
- In container: `/etc/tams/config.yaml` (mounted from host)
- The `Settings` class automatically detects the correct config path
- Environment variables can override config values (prefixed with `TAMS_`)

### Notes

- Scripts are executable and can be run directly with `python`
- All scripts use dependency injection - no manual connection setup needed
- Scripts work in both container and development environments
- Make sure the container has access to the VAST database and S3 storage

## Logging

Logs are handled in multiple ways:

1. **Console logs** (stdout/stderr) - View with `docker logs tams-api`
2. **File logs** - Written to `/app/logs/` inside container, persisted via `logs_data` volume
3. **Log files**:
   - `tams.log` - All logs (rotating, 10MB, 5 backups)
   - `tams_errors.log` - Error logs only (rotating, 10MB, 3 backups)

See [LOGGING.md](LOGGING.md) for detailed logging documentation.

### Quick Log Access

```bash
# View console logs
docker logs -f tams-api

# View log files
docker exec -it tams-api tail -f /app/logs/tams.log
docker exec -it tams-api tail -f /app/logs/tams_errors.log

# Copy logs to host
docker cp tams-api:/app/logs/tams.log ./
```

## Configuration

The server expects configuration at `/etc/tams/config.yaml` inside the container. This is mounted from the host via docker-compose:

```yaml
volumes:
  - ${CONFIG_FILE:-../config/config.yaml}:/etc/tams/config.yaml:ro
```

Set `CONFIG_FILE` environment variable to use a different config file:

```bash
export CONFIG_FILE=/path/to/production.yaml
docker-compose up
```

For production, you can use the example config:
```bash
export CONFIG_FILE=../docker/server/config/production.yaml.example
docker-compose up
```

## Environment Variables

- `TAMS_CONFIG_PATH` - Override config file path (default: `/etc/tams/config.yaml`)
- `TAMS_*` - Any setting can be overridden with `TAMS_` prefix (e.g., `TAMS_VAST_ENDPOINT`)

## Volumes

- `vast_data` - Persistent VAST database data
- `logs_data` - Application logs
- Config file mounted as read-only

## Networks

All services run on the `tams-network` bridge network for internal communication.

## Health Checks

All services include health checks:
- API: `http://localhost:8000/health`
- UI: `http://localhost/health`
- Trino: `http://localhost:8080/v1/status`

## Profiles

- `dev` - Development services (Trino)
- `prod` - Production services (UI, HAProxy)
- `full` - All services including observability stack
- `observability` - Prometheus, Grafana, etc.
