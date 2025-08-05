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
- User confirmation before deletion
- Detailed logging and reporting
- Error handling and rollback information

**Usage**:
```bash
cd mgmt
python cleanup_database.py
```

**Safety Features**:
- Requires explicit user confirmation
- Shows warning about data loss
- Lists all tables before deletion
- Provides detailed summary after completion

### `cleanup_database_auto.py`

**Purpose**: Automatic database cleanup without user confirmation.

**Use Cases**:
- Automated testing and CI/CD pipelines
- Scripted database resets
- Non-interactive environments

**Features**:
- Same safe deletion order as interactive version
- No user confirmation required
- Automatic execution
- Detailed logging and reporting

**Usage**:
```bash
cd mgmt
python cleanup_database_auto.py
```

**Warning**: This script will delete all data without confirmation!

### `cleanup_database_final.py`

**Purpose**: Complete database cleanup using VastDBManager directly.

**Use Cases**:
- Complete database reset
- Avoiding table recreation during cleanup
- Final cleanup before schema changes

**Features**:
- Uses VastDBManager directly (no table recreation)
- Safe deletion order
- No user confirmation required
- Proper connection cleanup

**Usage**:
```bash
cd mgmt
python cleanup_database_final.py
```

**Note**: This is the recommended script for completely clearing the database.

## Safety Warnings

⚠️ **WARNING**: These scripts can cause data loss!

- Always backup your data before running management scripts
- These scripts are designed for development and testing environments
- Use with extreme caution in production environments
- Some operations cannot be undone

## Prerequisites

- Python 3.8+
- Access to VAST database
- Proper environment configuration
- TAMS application dependencies installed

## Environment

Make sure your environment variables are properly configured:
- `VAST_ENDPOINT`
- `VAST_ACCESS_KEY`
- `VAST_SECRET_KEY`
- `VAST_BUCKET`
- `VAST_SCHEMA`
- `S3_ENDPOINT_URL`
- `S3_ACCESS_KEY_ID`
- `S3_SECRET_ACCESS_KEY`
- `S3_BUCKET_NAME`

## Directory Structure

```
mgmt/
├── README.md                    # This file
├── cleanup_database.py          # Interactive database cleanup script
├── cleanup_database_auto.py     # Automatic database cleanup script
├── cleanup_database_final.py    # Final database cleanup script (recommended)
└── ...                          # Future management scripts
``` 