# Storage Backends Database Implementation - October 27, 2025

## Summary
Implemented full storage backend management with database persistence, including CRUD operations, validation, and TAMS 8.0 compliance.

## New Module Structure

```
src/vasttams/storagebackends/
├── __init__.py          # Module initialization and exports
├── models.py            # Pydantic models for storage backends
├── service.py           # Business logic and database operations
├── router.py            # FastAPI endpoints
└── schemas.py           # PyArrow schemas for database
```

## Features Implemented

### 1. **Database Persistence**
- Storage backends stored in `storage_backends` table in VAST database
- Full schema with PyArrow types for nanosecond timestamps
- Table initialization on startup
- Projections for optimized queries

### 2. **CRUD Operations**
- `GET /service/storage-backends` - List all backends
- `POST /service/storage-backends` - Create new backend
- `GET /service/storage-backends/{id}` - Get specific backend
- `PUT /service/storage-backends/{id}` - Update backend
- `DELETE /service/storage-backends/{id}` - Delete backend (with validation)

### 3. **Validation Rules**
- **No deletion if objects exist**: DELETE returns 409 Conflict if any segments reference the backend
- **Updates allowed**: PUT can update any backend
- **Default backend management**: Only one backend can be marked as default
- **Label validation**: Labels must be alphanumeric with dashes/underscores only

### 4. **TAMS 8.0 Compliance**
- Implements ADR0032: Specifying storage backend when requesting allocation
- Implements ADR0038: Multiple managed instances
- Supports `storage_id` parameter in storage allocation requests
- Integrates with existing `/service/storage-backends` endpoint

## Key Implementation Details

### Service Layer
```python
class StorageBackendService:
    async def get_storage_backends() -> List[StorageBackend]
    async def get_storage_backend(id: str) -> StorageBackend
    async def create_storage_backend(backend: StorageBackendPost) -> StorageBackend
    async def update_storage_backend(id: str, update: StorageBackendPatch) -> StorageBackend
    async def delete_storage_backend(id: str) -> bool  # Raises 409 if objects exist
```

### Models
```python
class StorageBackend(BaseModel):
    id: str                    # UUID identifier
    label: Optional[str]       # Human-readable label
    store_type: str           # "http_object_store"
    provider: str              # "aws", "azure", "gcp", "minio"
    store_product: str         # "s3", "blob", "cloud-storage"
    region: Optional[str]      # "us-east-1"
    availability_zone: Optional[str]  # "a", "b", "c"
    default_storage: bool      # Only one backend can be default
    created_at: datetime       # Timestamp
    updated_at: datetime       # Timestamp
```

## Database Schema

```sql
CREATE TABLE storage_backends (
    id VARCHAR PRIMARY KEY,                    -- UUID
    label VARCHAR,                             -- Optional label
    store_type VARCHAR NOT NULL,               -- "http_object_store"
    provider VARCHAR NOT NULL,                 -- Cloud provider
    store_product VARCHAR NOT NULL,            -- Storage product
    region VARCHAR,                            -- Region
    availability_zone VARCHAR,                  -- AZ
    default_storage BOOLEAN DEFAULT FALSE,     -- Default flag
    created_at TIMESTAMP(9) WITH TIME ZONE,    -- Nanosecond precision
    updated_at TIMESTAMP(9) WITH TIME ZONE      -- Nanosecond precision
);
```

## Integration

1. **Main Service Integration**: `TAMSStorageService.get_storage_backends()` now uses the dedicated service
2. **Table Initialization**: Added to table creation order (after auth, before entities)
3. **Router Registration**: Registered in `main.py` alongside other resource routers
4. **OpenAPI Documentation**: Endpoints automatically documented

## Usage Examples

### Create a Storage Backend
```bash
POST /service/storage-backends
{
  "label": "production-s3-us-east-1",
  "store_type": "http_object_store",
  "provider": "aws",
  "store_product": "s3",
  "region": "us-east-1",
  "availability_zone": "a",
  "default_storage": true
}
```

### List Storage Backends
```bash
GET /service/storage-backends
```

### Update a Backend
```bash
PUT /service/storage-backends/{id}
{
  "label": "updated-label",
  "region": "us-west-2"
}
```

### Delete a Backend (blocked if objects exist)
```bash
DELETE /service/storage-backends/{id}
# Returns 409 if segments reference this backend
```

## Next Steps

1. **Management CLI**: Add CLI commands to manage storage backends
2. **Multiple Backends**: Support for tiered storage across backends
3. **Migration Tool**: Script to migrate objects between backends
4. **Monitoring**: Track object distribution across backends
5. **Performance Metrics**: Per-backend metrics and analytics

## Benefits

1. **Dynamic Configuration**: No code changes needed to add/remove backends
2. **Tiered Storage**: Support for hot/cold storage strategies
3. **Geographic Distribution**: Deploy backends across regions
4. **Cost Optimization**: Allocate objects to cost-effective backends
5. **TAMS 8.0 Compliance**: Full support for multiple storage backends per spec

