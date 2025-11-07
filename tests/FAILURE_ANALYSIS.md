# Test Failure Analysis

**Date**: 2025-11-06 (Updated 2025-01-06)  
**Total Tests**: 577  
**Status**: 456 passed, 33 failed, 88 skipped  
**Progress**: Reduced failures from 290 to 33 (89% reduction)

## Summary

After significant fixes (authentication, RBAC, test tracker), the remaining 33 failures fall into these categories:

1. **Router Test Failures**: ~12 failures
   - Flows router: 8 failures (likely API availability or test data issues)
   - Objects router: 6 failures
   - HLS router: 2 failures
   - Service router: 1 failure

2. **Service Layer Test Failures**: ~6 failures
   - Objects service: 4 failures
   - Segments service: 2 failures

3. **Database/Endpoint Test Failures**: ~4 failures
   - Objects database/endpoint: 2 failures
   - Flows database: 1 failure
   - Segments database: 1 failure

4. **Main Application Test Failures**: 1 failure
   - Lifespan events test

**Note**: Many tests pass when run individually but fail in parallel execution, suggesting:
- Test data conflicts (UUID collisions)
- API server overload during parallel runs
- Shared state issues
- Race conditions in test setup/teardown

## Failure Categories

### Category 1: Authentication Failures (CRITICAL)

**Count**: ~80 errors  
**Pattern**: All tests that depend on `auth_headers` fixture fail at setup  
**Error Message**: 
```
ERROR    conftest:conftest.py:90 CRITICAL: Failed to authenticate after 3 attempts. 
Server may not be running or credentials incorrect. All tests requiring authentication will fail.
```

**Root Cause**: 
- `auth_headers` fixture is session-scoped
- When tests run in parallel, multiple workers try to authenticate simultaneously
- Server may be overwhelmed or there's a race condition
- Authentication works when tested directly, but fails under parallel load

**Affected Tests**:
- All router comprehensive tests
- All endpoint tests
- All service tests that require authentication
- HLS router tests
- Auth endpoint tests
- Storage backend tests

**Solution**:
1. Increase retry count and delay in `auth_headers` fixture
2. Add connection pooling or rate limiting
3. Consider making `auth_headers` function-scoped instead of session-scoped for parallel execution
4. Add exponential backoff for retries

### Category 2: Test Code Issues (FIXED)

**Count**: 3 failures (now fixed)

1. **`tests/core/test_logging.py::TestEnhancedFormatter::test_formatter_creation_with_function`**
   - **Issue**: `EnhancedFormatter` doesn't store `include_function` as instance attribute
   - **Fix**: Updated test to verify behavior instead of attribute access

2. **`tests/core/test_logging.py::TestEnhancedFormatter::test_formatter_creation_without_function`**
   - **Issue**: Same as above
   - **Fix**: Updated test to verify behavior instead of attribute access

3. **`tests/looprecorder/test_manager.py::TestLoopRecorderManager::test_calculate_flow_duration`**
   - **Issue**: FlowSegment timerange must be TimeRange object, not string
   - **Fix**: Updated test to use `TimeRange(value="...")` instead of string

### Category 3: Data Validation Errors

**Count**: Various (need to investigate further)

**Pattern**: Tests fail with validation errors like:
- `Invalid MIME type format. Must be in format: type/subtype` (codec validation)
- `Field required` (essence_parameters missing)
- `Input should be a valid dictionary or instance of TimeRange` (timerange format)

**Examples**:
- Flow creation tests failing due to codec format (expects `video/H264` not `urn:x-nmos:codec:h264`)
- Missing `essence_parameters` in flow creation

**Solution**: 
- Review test data to ensure it matches TAMS 8.0 spec
- Update test fixtures to provide correct data formats
- Add validation helper functions for test data

### Category 4: Router Test Execution Issues

**Count**: ~80 errors (mostly due to auth failures)

**Pattern**: Router tests fail at setup due to authentication

**Affected Files**:
- `tests/flows/test_router_comprehensive.py`
- `tests/sources/test_router_comprehensive.py`
- `tests/segments/test_router_comprehensive.py`
- `tests/objects/test_router_comprehensive.py`
- `tests/hls/test_router_comprehensive.py`
- `tests/auth/test_endpoint.py`
- `tests/service/test_endpoint.py`

**Solution**: Fix authentication issues first, then re-run tests

## Recommended Fix Order

1. **Fix Authentication Issues** (Priority 1 - CRITICAL)
   - Modify `auth_headers` fixture to handle parallel execution better
   - Add exponential backoff
   - Consider function-scoped fixture for parallel tests
   - Test with reduced parallelism first

2. **Fix Test Code Issues** (Priority 2 - DONE)
   - ✅ Fixed logging tests
   - ✅ Fixed looprecorder test

3. **Fix Data Validation Issues** (Priority 3)
   - Review and fix test data formats
   - Ensure all required fields are provided
   - Validate against TAMS 8.0 spec

4. **Re-run Tests** (Priority 4)
   - Run full test suite after fixes
   - Verify authentication works under load
   - Check remaining failures

## Next Steps

1. Fix `auth_headers` fixture for parallel execution
2. Run tests with reduced parallelism to verify fixes
3. Fix any remaining data validation issues
4. Re-run full test suite
5. Update this document with results

## Notes

- Authentication works when tested directly (`python -c "import requests; ..."`)
- Server is running and accessible
- Issue appears to be related to parallel test execution
- Consider using `pytest-xdist` with `--dist=loadscope` to group tests by module
- May need to add connection pooling or rate limiting for auth requests
