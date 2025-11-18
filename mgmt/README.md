# TAMS Management Scripts

This directory contains management scripts for the TAMS (Time-addressable Media Store) API.

## Scripts

### `cleanup_database.py`

**Purpose**: Delete all tables from the VAST database to allow for a clean slate.

**Use Cases**:
- Recreating tables with updated schemas
- Removing all data for testing
- Preparing for fresh deployment

**Features**:
- Safe deletion order (handles dependencies)
- User confirmation before deletion (or use `--yes` flag)
- Dry-run mode with `--dry-run` flag
- Detailed logging and reporting
- Error handling

**Usage**:
```bash
# Interactive mode (requires confirmation)
python mgmt/cleanup_database.py

# Non-interactive mode (skip confirmation)
python mgmt/cleanup_database.py --yes

# Dry-run mode (see what would be deleted)
python mgmt/cleanup_database.py --dry-run
```

**Safety Features**:
- Requires explicit user confirmation (unless `--yes` is used)
- Shows warning about data loss
- Lists all tables before deletion
- Provides detailed summary after completion

### `delete_sources_by_label_filter.py`

**Purpose**: Delete sources by label prefix filter with cascade delete.

**Use Cases**:
- Clean up test data
- Remove sources matching specific naming patterns
- Bulk deletion with safety filters

**Features**:
- Filter by label prefix
- Negate filter option (`-n` flag for "all except X")
- Cascade delete (removes flows, segments, and objects)
- Preview before deletion
- User confirmation required

**Usage**:
```bash
# Delete all sources starting with "Test"
python mgmt/delete_sources_by_label_filter.py "Test"

# Delete all sources NOT starting with "Test" (all except "Test")
python mgmt/delete_sources_by_label_filter.py "Test" -n

# Delete all sources NOT starting with "Production"
python mgmt/delete_sources_by_label_filter.py "Production" -n
```

**Warning**: This performs cascade deletion - all flows, segments, and objects associated with deleted sources will also be removed.

### `user_mgmt.py`

**Purpose**: User management CLI for TAMS authentication system.

**Use Cases**:
- Create new users
- Delete users
- Update passwords
- Update user roles
- Initialize default users (admin, editor, viewer)

**Features**:
- Create users with roles (admin, editor, viewer)
- Delete users (soft or hard delete)
- Update passwords
- Update roles
- List all users
- Initialize default users with password 'vastdata'

**Usage**:
```bash
# Initialize default users (admin, editor, viewer with password 'vastdata')
python mgmt/user_mgmt.py init-default-users

# Create a new user
python mgmt/user_mgmt.py create <username> <role> [--password <password>]

# Delete a user
python mgmt/user_mgmt.py delete <username>

# Update password
python mgmt/user_mgmt.py update-password <username>

# Update role
python mgmt/user_mgmt.py update-role <username> <role>

# List all users
python mgmt/user_mgmt.py list
```

### `query_tables.py`

**Purpose**: Query and export data from TAMS database tables.

**Use Cases**:
- Export table data to JSON or CSV
- Get table statistics
- Inspect database contents
- Data migration and backup

**Features**:
- Query any TAMS table
- Export to JSON or CSV format
- Get table statistics
- Limit results
- List all available tables

**Usage**:
```bash
# List all tables
python mgmt/query_tables.py --list-tables

# Query a table and export to JSON
python mgmt/query_tables.py --table sources --format json

# Query with limit and export to CSV
python mgmt/query_tables.py --table flows --format csv --limit 100

# Get table statistics
python mgmt/query_tables.py --table segments --stats

# Export to file
python mgmt/query_tables.py --table users --format json --output users.json
```

### `get_db_version.py`

**Purpose**: Get VAST database version and configuration information.

**Use Cases**:
- Check database version
- Verify configuration
- Debug connection issues
- System information

**Features**:
- Shows VAST DB Python client version
- Shows VAST database version
- Displays configuration information
- Tests imports

**Usage**:
```bash
python mgmt/get_db_version.py
```

### `create_table_projections.py`

**Purpose**: Show table projection status (DEPRECATED).

**Note**: This script is deprecated as projections are now managed automatically during table initialization. It is kept for informational purposes only.

**Usage**:
```bash
# Show projection status
python mgmt/create_table_projections.py --status
```

### `generate_openapi.py`

**Purpose**: Generate OpenAPI JSON specification from the TAMS FastAPI application.

**Use Cases**:
- Generate API documentation
- Export OpenAPI schema for external tools
- Update API specification files

**Features**:
- Generates OpenAPI 3.0 specification
- Exports to JSON format
- Shows endpoint count

**Usage**:
```bash
python mgmt/generate_openapi.py
```

**Output**: Creates `api/openapi.json` with the complete OpenAPI specification.

### `generate_self_signed_cert.sh`

**Purpose**: Generate self-signed SSL certificate for development/testing.

**Usage**:
```bash
bash mgmt/generate_self_signed_cert.sh
```

## Safety Warnings

⚠️ **WARNING**: These scripts can cause data loss!

- Always backup your data before running management scripts
- These scripts are designed for development and testing environments
- Use with extreme caution in production environments
- Some operations cannot be undone
- Cascade delete operations will remove dependent data

## Prerequisites

- Python 3.12+
- Access to VAST database
- Proper environment configuration
- TAMS application dependencies installed

## Environment Configuration

Scripts use the same configuration as the TAMS server. Make sure your `config/config.yaml` is properly configured with:

- `vast_endpoint`
- `vast_access_key`
- `vast_secret_key`
- `vast_bucket`
- `vast_schema`
- `s3_endpoint_url`
- `s3_access_key_id`
- `s3_secret_access_key`
- `s3_bucket_name`

## Running Scripts in Docker Container

All management scripts are available inside the Docker container at `/app/mgmt/`.

### Execute Scripts in Container

```bash
# List users
docker exec -it tams-api python /app/mgmt/user_mgmt.py list

# Initialize default users
docker exec -it tams-api python /app/mgmt/user_mgmt.py init-default-users

# Query tables
docker exec -it tams-api python /app/mgmt/query_tables.py --list-tables

# Cleanup database
docker exec -it tams-api python /app/mgmt/cleanup_database.py --yes

# Delete sources by label
docker exec -it tams-api python /app/mgmt/delete_sources_by_label_filter.py "Test"

# Get database version
docker exec -it tams-api python /app/mgmt/get_db_version.py

# Generate OpenAPI spec
docker exec -it tams-api python /app/mgmt/generate_openapi.py
```

### Container Configuration

- Scripts automatically detect container vs development environment
- In container: config is at `/etc/tams/config.yaml` (mounted from host)
- In development: config is at `config/config.yaml`
- The `Settings` class handles path resolution automatically

## Notes

- All scripts use dependency injection (`get_vast_db()`, `get_s3_client()`) - no manual connection initialization needed
- Logging is automatically initialized at startup - no need to configure logging in scripts
- Scripts should be run from the project root directory (or use full paths in container)
- Scripts work in both container and development environments
- Test data generation scripts are located in `tests/` directory

## Directory Structure

```
mgmt/
├── README.md                          # This file
├── cleanup_database.py                # Database cleanup script
├── delete_sources_by_label_filter.py  # Delete sources by label prefix filter
├── user_mgmt.py                       # User management CLI
├── query_tables.py                    # Query and export table data
├── get_db_version.py                  # Get database version info
├── create_table_projections.py        # Show projection status (deprecated)
├── generate_openapi.py                # Generate OpenAPI specification
└── generate_self_signed_cert.sh      # Generate SSL certificate
```
