# Soft Delete Extension Documentation

## Overview

This document describes the **Soft Delete Extension** to the official TAMS (Time-addressable Media Store) API specification. This is a vendor-specific enhancement that provides data safety and audit capabilities beyond the base specification.

## Extension Status

- **Type**: Vendor-specific enhancement
- **Compliance**: NOT part of the official TAMS API specification
- **Status**: Implemented and active by default
- **Version**: 1.0

## What is Soft Delete?

Soft delete is a data management technique where records are marked as "deleted" rather than being physically removed from the database. This provides several benefits:

- **Data Recovery**: Deleted records can be restored
- **Audit Trail**: Complete history of who deleted what and when
- **Data Integrity**: Maintains referential relationships
- **Compliance**: Meets regulatory requirements for data retention

## Schema Extensions

### Database Schema Changes

All database tables include additional soft delete fields:

```sql
-- Example schema extension for sources table
ALTER TABLE sources ADD COLUMN deleted BOOLEAN DEFAULT FALSE;
ALTER TABLE sources ADD COLUMN deleted_at TIMESTAMP;
ALTER TABLE sources ADD COLUMN deleted_by VARCHAR(255);
```

### JSON Schema Extensions

The following fields are added to all entity schemas:

```json
{
  "deleted": {
    "type": "boolean",
    "description": "Flag indicating if record is soft-deleted",
    "default": false
  },
  "deleted_at": {
    "type": "string",
    "format": "date-time",
    "description": "ISO 8601 timestamp when record was soft-deleted",
    "nullable": true
  },
  "deleted_by": {
    "type": "string",
    "description": "User/system identifier that performed the soft deletion",
    "nullable": true
  }
}
```

## API Extensions

### Delete Endpoint Parameters

All delete endpoints (`DELETE /sources/{id}`, `DELETE /flows/{id}`, `DELETE /flows/{id}/segments`, `DELETE /objects/{id}`) support these additional query parameters:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `soft_delete` | boolean | `true` | Perform soft delete (flag as deleted) or hard delete (remove from database) |
| `cascade` | boolean | `true` | Cascade delete to associated records |
| `deleted_by` | string | `"system"` | User/system performing the deletion |

### Examples

#### Soft Delete a Source
```bash
# Default behavior (soft delete with cascade)
DELETE /sources/123e4567-e89b-12d3-a456-426614174000

# Explicit soft delete
DELETE /sources/123e4567-e89b-12d3-a456-426614174000?soft_delete=true&cascade=true&deleted_by=user123
```

#### Hard Delete a Source
```bash
# Hard delete with cascade (removes from database)
DELETE /sources/123e4567-e89b-12d3-a456-426614174000?soft_delete=false&cascade=true&deleted_by=admin
```

#### Soft Delete a Flow Without Cascade
```bash
# Soft delete flow but preserve segments
DELETE /flows/456e7890-e89b-12d3-a456-426614174000?soft_delete=true&cascade=false&deleted_by=editor
```

#### Hard Delete Flow Segments
```bash
# Hard delete segments (removes S3 data)
DELETE /flows/456e7890-e89b-12d3-a456-426614174000/segments?soft_delete=false&deleted_by=admin
```

## Cascade Delete Behavior

### Source Deletion
When a source is deleted with `cascade=true`:
1. Source is marked as deleted (soft) or removed (hard)
2. All associated flows are deleted with the same method
3. All associated segments are deleted with the same method
4. If hard delete, S3 data is also removed

### Flow Deletion
When a flow is deleted with `cascade=true`:
1. Flow is marked as deleted (soft) or removed (hard)
2. All associated segments are deleted with the same method
3. If hard delete, S3 data is also removed

### Segment Deletion
When segments are deleted:
1. Segments are marked as deleted (soft) or removed (hard)
2. If hard delete, S3 data is also removed
3. No cascade behavior (segments are leaf nodes)

### Object Deletion
When objects are deleted:
1. Object is marked as deleted (soft) or removed (hard)
2. No cascade behavior (objects are standalone)

## Query Behavior

### Automatic Filtering

**Important**: This extension automatically excludes soft-deleted records from all query operations by default. This ensures data consistency and prevents accidental exposure of deleted data.

### Current Implementation Status

| Endpoint | Soft Delete Filtering | Status |
|----------|----------------------|--------|
| `GET /sources` | ✅ Implemented | Automatically excludes soft-deleted sources |
| `GET /flows` | ✅ Implemented | Automatically excludes soft-deleted flows |
| `GET /flows/{id}/segments` | ✅ Implemented | Automatically excludes soft-deleted segments |
| `GET /objects/{id}` | ✅ Implemented | Automatically excludes soft-deleted objects |

### Query Examples

```bash
# List sources (excludes soft-deleted)
GET /sources

# List flows (excludes soft-deleted)
GET /flows

# List segments (excludes soft-deleted)
GET /flows/123e4567-e89b-12d3-a456-426614174000/segments
```

## Data Recovery

### Restore Operations

Soft-deleted records can be restored using internal API endpoints:

```bash
# Restore a soft-deleted source
POST /internal/restore/sources/123e4567-e89b-12d3-a456-426614174000

# Restore a soft-deleted flow
POST /internal/restore/flows/456e7890-e89b-12d3-a456-426614174000
```

**Note**: Restore operations do not automatically restore child records. Each record must be restored individually.

### Audit Trail

All soft delete operations are logged with:
- Timestamp of deletion
- User/system that performed the deletion
- Method used (soft vs hard)
- Cascade behavior
- Affected record IDs

## Configuration

### Environment Variables

Soft delete behavior can be configured through environment variables:

```bash
# Enable/disable soft delete functionality
SOFT_DELETE_ENABLED=true

# Default soft delete behavior
DEFAULT_SOFT_DELETE=true
DEFAULT_CASCADE_DELETE=true

# Audit logging
SOFT_DELETE_AUDIT_ENABLED=true
```

### Database Configuration

```sql
-- Enable soft delete on specific tables
UPDATE sources SET deleted = false WHERE deleted IS NULL;
UPDATE flows SET deleted = false WHERE deleted IS NULL;
UPDATE segments SET deleted = false WHERE deleted IS NULL;
UPDATE objects SET deleted = false WHERE deleted IS NULL;
```

## Compliance and Standards

### Official TAMS Specification

This soft delete functionality is **NOT part of the official TAMS API specification**. The official specification does not define:

- Soft delete fields in schemas
- Deleted state filtering parameters
- Restore operations
- Audit trail requirements

### Compliance Options

Implementations that require strict compliance with the official specification should:

1. **Disable Soft Delete**: Set `SOFT_DELETE_ENABLED=false`
2. **Document as Extension**: Clearly mark this as a non-standard enhancement
3. **Implement Official Spec**: Remove all soft delete functionality

### Vendor-Specific Enhancement

This extension is implemented as a vendor-specific enhancement that:

- Maintains backward compatibility with the official specification
- Provides additional data safety features
- Can be disabled for compliance requirements
- Is clearly documented as an extension

## Implementation Details

### Database Layer

The soft delete functionality is implemented at the database layer using:

- **VAST Database**: Columnar storage with soft delete fields
- **Query Filtering**: Automatic predicate injection for soft delete filtering
- **Transaction Support**: ACID-compliant soft delete operations

### Application Layer

The application layer provides:

- **API Extensions**: Additional query parameters for delete operations
- **Business Logic**: Cascade delete and restore operations
- **Audit Logging**: Complete audit trail of all operations

### Storage Layer

The storage layer handles:

- **S3 Integration**: Conditional deletion of media segments
- **Metadata Preservation**: Soft delete preserves S3 metadata
- **Data Recovery**: Restore operations for S3 data

## Future Enhancements

### Planned Features

1. **Query Parameters**: Add `include_deleted`, `deleted_only`, `deleted_state` parameters
2. **Bulk Operations**: Bulk restore and hard delete operations
3. **Retention Policies**: Automatic cleanup of old soft-deleted records
4. **Advanced Filtering**: Filter by deletion date, user, etc.

### Proposed API Extensions

```bash
# Include soft-deleted records in queries
GET /sources?include_deleted=true

# Show only soft-deleted records
GET /sources?deleted_only=true

# Filter by deletion state
GET /sources?deleted_state=all

# Filter by deletion date
GET /sources?deleted_after=2024-01-01T00:00:00Z

# Filter by user who deleted
GET /sources?deleted_by=user123
```

## Troubleshooting

### Common Issues

1. **Soft-deleted records appearing in queries**: Check if soft delete filtering is implemented for the specific endpoint
2. **Cascade delete not working**: Verify cascade parameter is set to `true`
3. **S3 data not deleted**: Ensure `soft_delete=false` for hard delete operations
4. **Restore operations failing**: Check if record exists and is soft-deleted

### Debug Commands

```bash
# Check soft delete status of a record
GET /internal/debug/sources/123e4567-e89b-12d3-a456-426614174000

# List all soft-deleted records
GET /internal/debug/deleted/sources

# Check cascade relationships
GET /internal/debug/cascade/sources/123e4567-e89b-12d3-a456-426614174000
```

## Support

For questions about the soft delete extension:

1. Check this documentation
2. Review the implementation code
3. Run the test suite for examples
4. Contact the development team

---

**Note**: This extension is provided as-is and may be modified or removed in future versions. Always test thoroughly in your environment before using in production. 