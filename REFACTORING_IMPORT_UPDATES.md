# Refactoring Import Updates Required

## Status
Phase 1 and 2 complete: Files have been moved to new resource-based structure.
Phase 3 in progress: Import updates needed.

## Summary of Changes

### Files Moved Successfully
- Common module structure created
- Resource modules (flows, sources, objects, segments, service) created
- Files moved to their new locations

### Import Updates Needed

The following files need their imports updated to match the new structure:

#### Pattern Changes:
1. `from ..models import X` → `from .models import X` (local) or `from ..common.models import X` (shared)
2. `from ..storage import X` → `from ..common.storage import X`
3. `from ..core` → unchanged (stays as-is)

#### Files That Need Updates:

**app/flows/router.py** - PARTIALLY DONE
- ✅ Changed to use local models and common
- ⚠️ Needs: Check for response models (FlowsResponse)

**app/flows/service.py** 
- Update imports from `..models` to `..common.models` or `..flows.models`
- Update imports from `..storage` to `..common.storage`
- Import `Tags` from `..common.models`

**app/sources/router.py**
- Update imports like flows router
- Import response models from common

**app/sources/service.py**
- Update model imports
- Import `Tags` from `..common.models`

**app/objects/router.py**
- Update imports to new structure

**app/objects/service.py**
- Update model imports

**app/segments/router.py**
- Update imports

**app/segments/service.py**
- Update model imports

**app/service/router.py**
- Update imports
- Merge deletion_router.py into this file

**app/service/deletion_router.py**
- May need to merge into router.py or keep separate

**app/main.py**
- Update router imports:
  - `from .api.flows_router` → `from .flows.router`
  - `from .api.sources_router` → `from .sources.router`
  - `from .api.objects_router` → `from .objects.router`
  - `from .api.segments_router` → `from .segments.router`
  - `from .api.service_router` → `from .service.router`
- Update storage service import from `app.storage` to `app.common.storage`

**app/common/storage/main_service.py**
- Update imports for service classes:
  - `from app.storage.flow_service` → `from app.flows.service`
  - `from app.storage.source_service` → `from app.sources.service`
  - `from app.storage.object_service` → `from app.objects.service`
  - `from app.storage.segment_service` → `from app.segments.service`
- Update tag service imports

**app/core/dependencies.py**
- Fix VAST imports:
  - `from ..vaststore.vastdbmanager` → `from vastdbmanager import`
  - `from ..vaststore.s3` → `from vasts3 import`

## Next Steps

1. Update all imports in moved files using find/replace patterns
2. Update main.py router registrations
3. Fix response models location (maybe move to common/responses.py)
4. Update service router to merge deletion endpoints properly
5. Test each module independently
6. Run full application tests

## Files That May Need Special Attention

- **app/models/legacy.py** - Check if still needed
- **app/models/models.py** - Check if it's just re-exports
- **app/main_clean.py** - Check if it's a duplicate

## Testing Strategy

After import updates:
1. Run linter to catch import errors
2. Test each router endpoint
3. Verify storage services initialize
4. Check that all dependencies resolve correctly

