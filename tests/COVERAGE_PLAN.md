# 100% Test Coverage Plan

**NOTE: This file is deprecated. See `COVERAGE_TRACKING.md` for current status.**

## Current Status: 28.75% Coverage (2,596 of 9,031 statements)

## Priority Areas for Coverage

### 1. Router Files (0% coverage) - HIGHEST PRIORITY
All API endpoints need comprehensive test coverage:

- [ ] `flows/router.py` (402 lines) - 0% coverage
- [ ] `sources/router.py` (331 lines) - 0% coverage  
- [ ] `segments/router.py` (239 lines) - 0% coverage
- [ ] `objects/router.py` (113 lines) - 0% coverage
- [ ] `auth/router.py` (156 lines) - 0% coverage
- [ ] `analytics/router.py` (37 lines) - 0% coverage
- [ ] `hls/router.py` (50 lines) - 0% coverage
- [ ] `storagebackends/router.py` (38 lines) - 0% coverage
- [ ] `service/router.py` (30 lines) - 0% coverage
- [ ] `webhooks/router.py` (53 lines) - 45% coverage (needs improvement)
- [ ] `service/deletion_router.py` (28 lines) - 0% coverage

**Total Router Lines: ~1,440 lines needing coverage**

### 2. Service Files (5-15% coverage) - HIGH PRIORITY
Business logic layer needs comprehensive testing:

- [ ] `objects/service.py` (512 lines) - 5% coverage
- [ ] `segments/service.py` (511 lines) - 5% coverage
- [ ] `sources/service.py` (289 lines) - 7% coverage
- [ ] `flows/service.py` (430 lines) - 7% coverage
- [ ] `webhooks/service.py` (180 lines) - 8% coverage
- [ ] `events/manager.py` (208 lines) - 11% coverage
- [ ] `analytics/service.py` (188 lines) - 0% coverage
- [ ] `storagebackends/service.py` (242 lines) - 0% coverage
- [ ] `auth/service.py` (85 lines) - 0% coverage
- [ ] `common/tags/service.py` (203 lines) - 15% coverage

**Total Service Lines: ~3,258 lines needing coverage**

### 3. Analytics Module (0% coverage) - MEDIUM PRIORITY
- [ ] `analytics/router.py` - 0% coverage
- [ ] `analytics/service.py` - 0% coverage
- [ ] `analytics/models.py` - 0% coverage

**Total Analytics Lines: ~281 lines**

### 4. Schema Files (0% coverage) - MEDIUM PRIORITY
- [ ] `flows/schemas.py` - 0% coverage
- [ ] `sources/schemas.py` - 0% coverage
- [ ] `objects/schemas.py` - 0% coverage
- [ ] `segments/schemas.py` - 0% coverage
- [ ] `service/schemas.py` - 0% coverage
- [ ] `storagebackends/schemas.py` - 0% coverage

**Total Schema Lines: ~60 lines**

### 5. Core Application (0% coverage) - LOW PRIORITY
- [ ] `main.py` (192 lines) - 0% coverage
- [ ] `looprecorder/manager.py` (133 lines) - 0% coverage

## Implementation Strategy

### Phase 1: Router Tests (Target: All routers at 80%+)
1. Create comprehensive router test files for each module
2. Test all HTTP methods (GET, POST, PUT, DELETE, HEAD, OPTIONS)
3. Test error handling (400, 401, 404, 422, 500)
4. Test authentication/authorization
5. Test query parameters and filters
6. Test request validation

### Phase 2: Service Layer Tests (Target: All services at 80%+)
1. Unit tests for business logic
2. Mock dependencies (database, S3, etc.)
3. Test edge cases and error conditions
4. Test data transformations
5. Test validation logic

### Phase 3: Integration Tests (Target: End-to-end coverage)
1. Test full workflows
2. Test cross-module interactions
3. Test database operations
4. Test event delivery

### Phase 4: Remaining Coverage (Target: 100%)
1. Schema validation tests
2. Utility function tests
3. Error handler tests
4. Background task tests

## Test File Structure

```
tests/
├── routers/              # NEW: Router endpoint tests
│   ├── test_flows_router.py
│   ├── test_sources_router.py
│   ├── test_segments_router.py
│   ├── test_objects_router.py
│   ├── test_auth_router.py
│   ├── test_analytics_router.py
│   ├── test_hls_router.py
│   ├── test_storagebackends_router.py
│   ├── test_service_router.py
│   └── test_webhooks_router.py
├── services/             # NEW: Service layer tests
│   ├── test_flows_service.py
│   ├── test_sources_service.py
│   ├── test_segments_service.py
│   ├── test_objects_service.py
│   ├── test_analytics_service.py
│   ├── test_storagebackends_service.py
│   └── test_webhooks_service.py
├── schemas/              # NEW: Schema validation tests
│   ├── test_flow_schemas.py
│   ├── test_source_schemas.py
│   ├── test_object_schemas.py
│   └── test_segment_schemas.py
└── [existing test files]
```

## Progress Tracking

- **Router Tests**: 9/11 complete (test files created, but need to run to get coverage)
- **Service Tests**: 0/10 complete
- **Schema Tests**: 0/6 complete
- **Overall Coverage**: 20% (1,779 of 9,031 statements) → Target: 100%

## Current Status (2025-11-05)

### Completed
- ✅ Created comprehensive router tests for:
  - flows/router.py (41 tests)
  - analytics/router.py (4 tests)
  - objects/router.py (8 tests)
  - sources/router.py (30+ tests)
  - segments/router.py (10+ tests)
  - hls/router.py (4 tests)
  - storagebackends/router.py (10+ tests)
  - service/router.py (3 tests)
  - auth/router.py (10+ tests)
- ✅ Fixed segments router GetUrl validation error
- ✅ Reduced verbose authentication log messages
- ✅ Created parallel test runner script

### Issues
- Router tests exist but are not being executed (all skipped)
- Router coverage still at 0% despite test files existing
- Need to investigate why router tests are being skipped

## Estimated Lines to Test

- **Routers**: ~1,440 lines
- **Services**: ~3,258 lines
- **Schemas**: ~60 lines
- **Other**: ~325 lines
- **Total**: ~5,083 lines needing test coverage

