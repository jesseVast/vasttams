# TAMS Server Docker Configuration

This directory contains Docker configuration files for the TAMS FastAPI server.

## Files

- `Dockerfile` - Server container image
- `config/` - Configuration examples
  - `production.yaml.example` - Production configuration template
- `haproxy/` - HAProxy configuration for S3 proxying
- `trino/` - Trino configuration files
- `BUILD.md` - Detailed build instructions
- `LOGGING.md` - Logging configuration documentation
- `start-observability.sh` - Script to start observability stack

## Building the Server Container

### Using docker-compose (Recommended)

```bash
cd docker
docker-compose build tams-api
```

### Manual Build

From the project root:

```bash
docker build -f docker/server/Dockerfile -t tams-api .
```

See `BUILD.md` for detailed build instructions and troubleshooting.

## Configuration

The server expects configuration at `/etc/tams/config.yaml` inside the container.

### Development

Uses `config/config.yaml` from the project root (mounted via docker-compose).

### Production

Use the example config as a template:

```bash
cp docker/server/config/production.yaml.example docker/server/config/production.yaml
# Edit production.yaml with your values
export CONFIG_FILE=../docker/server/config/production.yaml
docker-compose up
```

## Related Documentation

- `BUILD.md` - Build instructions and troubleshooting
- `LOGGING.md` - Logging configuration and management
- `../README.md` - Main Docker documentation

