# Comprehensive Test Preparation Plan

## Current Test Inventory

### Existing Router Tests (Created but not executing)
- ✅ `tests/flows/test_router_comprehensive.py` - 42 tests
- ✅ `tests/sources/test_router_comprehensive.py` - 28 tests  
- ✅ `tests/analytics/test_router.py` - 4 tests
- ✅ `tests/objects/test_router_comprehensive.py` - 8 tests
- ✅ `tests/segments/test_router_comprehensive.py` - 9 tests
- ✅ `tests/hls/test_router_comprehensive.py` - 5 tests
- ✅ `tests/storagebackends/test_router_comprehensive.py` - 7 tests
- ✅ `tests/service/test_router_comprehensive.py` - 3 tests
- ✅ `tests/auth/test_router_comprehensive.py` - 9 tests
- ✅ `tests/service/test_deletion_router.py` - 2 tests (NEW)
- ⚠️ `tests/webhooks/test_endpoint.py` - exists but needs router coverage

### Existing Service Tests
- ✅ `tests/services/test_analytics_service.py` - 8 tests (NEW)
- ✅ `tests/services/test_flows_service.py` - 11 tests (NEW)
- ✅ `tests/services/test_sources_service.py` - 4 tests (NEW)
- ✅ `tests/services/test_segments_service.py` - 4 tests (NEW)
- ❌ Additional service tests still needed (objects, storagebackends, webhooks, auth, events, tags)

### Existing Schema Tests
- ✅ `tests/schemas/test_flow_schemas.py` - 7 tests (NEW)
- ✅ `tests/schemas/test_source_schemas.py` - 5 tests (NEW)
- ❌ Additional schema tests still needed (objects, segments, service, storagebackends)

### Other Missing Tests
- ❌ `analytics/service.py` - 0% coverage
- ❌ `analytics/models.py` - 0% coverage
- ❌ `main.py` - 0% coverage
- ❌ `looprecorder/manager.py` - 0% coverage

## Action Plan

### Phase 1: Fix Router Test Execution (IMMEDIATE)
**Problem**: Router tests exist but are all being skipped
**Solution**: 
1. Investigate why `api_available` fixture is failing
2. Fix fixture dependencies
3. Ensure tests actually run

### Phase 2: Create Service Layer Tests (HIGH PRIORITY)
Create unit tests for all service files:
1. `tests/services/test_flows_service.py`
2. `tests/services/test_sources_service.py`
3. `tests/services/test_segments_service.py`
4. `tests/services/test_objects_service.py`
5. `tests/services/test_analytics_service.py`
6. `tests/services/test_storagebackends_service.py`
7. `tests/services/test_webhooks_service.py`
8. `tests/services/test_auth_service.py`
9. `tests/services/test_events_service.py`
10. `tests/services/test_tags_service.py`

### Phase 3: Create Schema Validation Tests (MEDIUM PRIORITY)
1. `tests/schemas/test_flow_schemas.py`
2. `tests/schemas/test_source_schemas.py`
3. `tests/schemas/test_object_schemas.py`
4. `tests/schemas/test_segment_schemas.py`
5. `tests/schemas/test_service_schemas.py`
6. `tests/schemas/test_storagebackends_schemas.py`

### Phase 4: Create Missing Router Tests
1. `tests/service/test_deletion_router.py` - for deletion_router.py
2. Improve `tests/webhooks/test_endpoint.py` to cover router.py completely

### Phase 5: Create Analytics Module Tests
1. `tests/analytics/test_service.py` - for analytics/service.py
2. `tests/analytics/test_models.py` - for analytics/models.py

### Phase 6: Create Other Module Tests
1. `tests/main/test_main.py` - for main.py (app initialization)
2. `tests/looprecorder/test_manager.py` - for looprecorder/manager.py

## Implementation Priority

1. **URGENT**: Fix router test execution (why are they skipped?)
2. **HIGH**: Create service layer tests (3,258 lines at 0-15% coverage)
3. **MEDIUM**: Create schema validation tests
4. **MEDIUM**: Complete router coverage (deletion_router, webhooks)
5. **LOW**: Analytics, main, looprecorder modules

## Target Coverage Goals

- **Routers**: 80%+ (currently 0%)
- **Services**: 80%+ (currently 0-15%)
- **Schemas**: 80%+ (currently 0%)
- **Overall**: 100% (currently 20%)

