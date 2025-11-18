# TAMS UI Docker Configuration

This directory contains Docker configuration files for the TAMS React UI.

## Files

- `Dockerfile.ui` - Multi-stage build for React UI with nginx
- `nginx.conf` - Nginx configuration for serving the UI and proxying API requests

## Building the UI Container

### Using docker-compose (Recommended)

```bash
cd docker
docker-compose --profile prod build tams-ui
```

### Manual Build

From the project root:

```bash
docker build -f docker/ui/Dockerfile.ui -t tams-ui .
```

## Architecture

The UI container uses a multi-stage build:

1. **Builder Stage**: Node.js Alpine image
   - Installs dependencies
   - Builds the React application
   - Sets `REACT_APP_API_URL=/api` for API proxying

2. **Production Stage**: Nginx Alpine image
   - Serves static files from `/usr/share/nginx/html`
   - Proxies `/api/*` requests to the backend (`tams-api:8000`)
   - Includes health check endpoint at `/health`

## Nginx Configuration

The `nginx.conf` file:
- Serves the React app with client-side routing support
- Proxies API requests from `/api` to the backend
- Includes gzip compression and security headers
- Caches static assets for 1 year
- Provides a health check endpoint

## Running the UI

The UI is included in docker-compose with the `prod` or `full` profile:

```bash
# Production mode (includes UI)
docker-compose --profile prod up

# Full stack (includes UI and observability)
docker-compose --profile full up
```

The UI will be available at `http://localhost` (port 80).

## Environment Variables

- `REACT_APP_API_URL` - API base URL (default: `/api` for nginx proxy)
  - Set during build time via `ARG REACT_APP_API_URL`
  - Used by the React app to make API calls

## Health Check

The UI container includes a health check endpoint at `/health` that returns `200 OK` when nginx is running.

