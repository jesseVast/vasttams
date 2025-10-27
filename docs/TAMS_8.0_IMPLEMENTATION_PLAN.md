# TAMS 8.0 Complete Upgrade Plan

## Overview

Upgrade the TAMS implementation to full 8.0 specification compliance, addressing breaking changes, missing features, and enhanced capabilities.

## Phase 1: Critical Model Changes (Breaking)

### 1.1 Video Flow VFR Support (ADR-0041)

**Files**: `app/models/flows.py`

Add Variable Frame Rate support to video flows:

- Add `vfr: Optional[bool] = Field(default=False)` to `VideoEssenceParameters`
- Add validation: if `vfr=True`, `frame_rate` must be None
- Add validation: if `vfr=False` or None, `frame_rate` must be set
- Update model docstrings to explain VFR behavior

### 1.2 Tags Array Support (ADR-0040)

**Files**: `app/models/core.py`, `app/storage/tag_service.py`, `app/storage/tag_manager.py`

Update Tags to support both string and array values:

- Change `Tags(RootModel[Dict[str, str]])` to `Tags(RootModel[Dict[str, Union[str, List[str]]]])`
- Update tag validation in `tag_manager.py` to handle arrays
- Update tag standardization to preserve array types
- Update tag filtering logic to support "at least one match" behavior

### 1.3 Object Model TimeRange (ADR-0027)

**Files**: `app/models/objects.py`

Add timerange field to Object model:

- Add `timerange: TimeRange = Field(...)` as required field
- Update Object creation logic to calculate/store timerange
- Update storage service to populate timerange from media

## Phase 2: Missing Critical Endpoints

### 2.1 Object Instances Management (ADR-0038)

**Files**: `app/api/objects_router.py`, `app/storage/object_service.py`, `app/models/objects.py`

Implement Object Instance endpoints:

- `POST /objects/{objectId}/instances` - Register new instance with mandatory `label` for uncontrolled
- `GET /objects/{objectId}/instances` - List all instances
- `DELETE /objects/{objectId}/instances` - Delete specific instance by label or storage_id
- Add `ObjectInstance` model with fields: `label`, `storage_id`, `url`, `controlled`
- Update Object model to include `instances` list

### 2.2 Webhook Tags Support (ADR-0040)

**Files**: `app/models/webhooks.py`, `app/api/service_router.py`

Add tags to webhooks:

- Add `tags: Optional[Tags]` field to Webhook model
- Add `tag.{name}` query parameter to `GET /service/webhooks`
- Add `tag_exists.{name}` query parameter
- Implement tag filtering in webhook list endpoint

### 2.3 Storage Backends Endpoint

**Files**: `app/api/service_router.py`, `app/models/storage.py`

Implement storage backends listing:

- Add `GET /service/storage-backends` endpoint
- Return list of available storage backends with their properties
- Use existing `StorageBackend` model
- Populate from configuration

## Phase 3: Query Parameter Enhancements

### 3.1 Flow Tags Filtering

**Files**: `app/api/flows_router.py`, `app/storage/flow_service.py`

Add tag-based filtering to flows:

- Add `tag.{name}` query parameter parsing (dynamic parameter names)
- Add `tag_exists.{name}` query parameter parsing
- Implement tag matching logic for both string and array values
- Support comma-separated values for "OR" queries

### 3.2 Source Tags Filtering

**Files**: `app/api/sources_router.py`, `app/storage/source_service.py`

Add tag-based filtering to sources:

- Add `tag.{name}` query parameter parsing
- Add `tag_exists.{name}` query parameter parsing
- Implement tag matching logic

### 3.3 Object Flow Tags Filtering

**Files**: `app/api/objects_router.py`, `app/storage/object_service.py`

Add flow tag filtering to objects:

- Add `flow_tag.{name}` query parameter to `GET /objects/{objectId}`
- Add `flow_tag_exists.{name}` query parameter
- Filter `referenced_by_flows` list based on flow tags
- Requires joining object-flow relationships with flow tags

### 3.4 Segment URL Filtering Verification (ADR-0023)

**Files**: `app/api/segments_router.py`

Verify segment filtering parameters:

- Confirm `accept_get_urls` works correctly
- Confirm `accept_storage_ids` works correctly
- Confirm `presigned` filtering works correctly
- Confirm `verbose_storage` parameter works

## Phase 4: Schema Compliance Verification

### 4.1 Timestamp Validation

**Files**: `app/models/core.py`

Verify timestamp format compliance:

- Pattern: `^-?(0|[1-9][0-9]*):(0|[1-9][0-9]{0,8})$`
- No leading zeros in seconds or nanoseconds
- Support negative timestamps
- Already implemented - run validation tests

### 4.2 TimeRange Validation

**Files**: `app/models/core.py`

Verify timerange format compliance:

- Support inclusivity markers: `[`, `]`, `(`, `)`
- Support empty timerange: `()`
- Support eternal timerange: `_`
- Support instantaneous timerange: `[timestamp]`
- Already implemented - run validation tests

### 4.3 UUID Validation

**Files**: `app/models/core.py`

Verify UUID format:

- Pattern: `^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$`
- Already implemented - verify compliance

## Phase 5: Database Schema Updates

### 5.1 Update Table Schemas

**Files**: `app/storage/schemas.py`

Update PyArrow schemas:

- Add `vfr` field to flows table (boolean)
- Update `tags` field type to support arrays (JSON/VARCHAR)
- Add `timerange` field to objects table
- Add `tags` field to webhooks table
- Add object_instances table with fields: id, object_id, label, storage_id, url, controlled

### 5.2 Table Initialization

**Files**: `app/storage/table_initializer.py`

Update table creation logic:

- Create object_instances table
- Update flows table for VFR field
- Ensure tags columns support JSON arrays
- Run table initialization script

## Phase 6: Storage Service Updates

### 6.1 Tag Service Array Support

**Files**: `app/storage/tag_service.py`

Update tag storage for arrays:

- Store array values correctly in database
- Retrieve and reconstruct array values
- Update tag queries to match array elements

### 6.2 Object Service Enhancements

**Files**: `app/storage/object_service.py`

Add object instance management:

- Implement `create_object_instance()`
- Implement `list_object_instances()`
- Implement `delete_object_instance()`
- Update `get_object()` to include instances

### 6.3 Flow Service VFR Handling

**Files**: `app/storage/flow_service.py`

Add VFR flow handling:

- Validate VFR/frame_rate mutual exclusivity
- Store VFR flag correctly
- Return VFR in flow responses

## Phase 7: Testing and Validation

### 7.1 Model Tests

**Files**: `tests/test_models/`

Create comprehensive model tests:

- Test VFR validation (frame_rate required when vfr=false)
- Test Tags with arrays (string and array values)
- Test Object timerange requirement
- Test all timestamp/timerange edge cases

### 7.2 Endpoint Tests

**Files**: `tests/test_endpoints/`

Test new/updated endpoints:

- Test object instances CRUD operations
- Test webhook tags filtering
- Test flow/source/object tag filtering
- Test storage backends listing

### 7.3 Integration Tests

**Files**: `tests/test_integration/`

End-to-end workflow tests:

- Create VFR video flow
- Create flow with array tags, filter by tags
- Create object with multiple instances
- Verify tag filtering across all resources

## Phase 8: Documentation Updates

### 8.1 Update API Documentation

**Files**: `README.md`, `docs/TAMS_API_ENDPOINTS.md`

Document TAMS 8.0 changes:

- List breaking changes (VFR, tags arrays)
- Document new endpoints (object instances, storage backends)
- Document new query parameters (tag filtering)
- Update examples with TAMS 8.0 features

### 8.2 Update Migration Guide

**Files**: `docs/MIGRATION_8.0.md` (new)

Create migration guide:

- List breaking changes and required updates
- Provide migration scripts for database
- Document API client changes needed
- Include example code for new features

## Phase 9: Vaststore Integration

### 9.1 Copy Vaststore Modules

**Files**: `app/vaststore/` (new directory)

Copy required vaststore modules:

- Copy `vastdbmanager/` package
- Copy `vasts3/` package
- Update `__init__.py` imports
- Preserve only necessary files

### 9.2 Update Imports

**Files**: Multiple across `app/storage/`, `app/core/`

Update vaststore references:

- Change imports from submodule to local package
- Update any configuration references
- Test database connectivity
- Test S3 connectivity

## Implementation Notes

- **Breaking Changes**: Phases 1 and 2 contain breaking changes
- **Database Migration**: Phase 5 requires database schema updates
- **Backward Compatibility**: Consider adding migration scripts for existing data
- **Testing Strategy**: Run tests after each phase
- **Deployment**: Will require server restart and database migration

## Task Checklist

- [ ] Add VFR boolean field and validation to VideoEssenceParameters in app/models/flows.py
- [ ] Update Tags model to support Dict[str, Union[str, List[str]]] in app/models/core.py
- [ ] Add required timerange field to Object model in app/models/objects.py
- [ ] Implement POST/GET/DELETE /objects/{objectId}/instances endpoints
- [ ] Add tags field to Webhook model and tag filtering to webhooks endpoint
- [ ] Implement GET /service/storage-backends endpoint
- [ ] Add tag.{name} and tag_exists.{name} query parameters to flows listing
- [ ] Add tag.{name} and tag_exists.{name} query parameters to sources listing
- [ ] Add flow_tag.{name} filtering to objects endpoint
- [ ] Update PyArrow schemas in app/storage/schemas.py for new fields
- [ ] Update tag storage service to handle array values correctly
- [ ] Implement object instance management in object storage service
- [ ] Add VFR validation and handling in flow storage service
- [ ] Create tests for VFR, tags arrays, and object timerange
- [ ] Create tests for new object instances and webhook tags endpoints
- [ ] Create end-to-end tests for TAMS 8.0 workflows
- [ ] Update README and create MIGRATION_8.0.md guide
- [ ] Copy vastdbmanager and vasts3 into app/vaststore/
- [ ] Update all imports to reference local vaststore package

