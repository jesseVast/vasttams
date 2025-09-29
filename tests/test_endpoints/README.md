# TAMS API Endpoint Tests

This directory contains comprehensive endpoint tests for the TAMS API, organized into focused modules for better maintainability and debugging.

## Test Structure

### Core Test Files

- **`test_utils.py`** - Shared utilities and helper functions
- **`test_runner.py`** - Main test runner for executing all or specific test modules

### Test Modules

1. **`test_core_service.py`** - Core service endpoints
   - Health check endpoints (`/health`)
   - Root endpoints (`/`)
   - Service information (`/service`)
   - Storage backends (`/service/storage-backends`)
   - OpenAPI specification (`/openapi.json`)
   - Metrics (`/metrics`)
   - Configuration endpoints

2. **`test_sources.py`** - Source management endpoints
   - CRUD operations (`/sources`)
   - Batch operations (`/sources/batch`)
   - Tags management (`/sources/{id}/tags`)
   - Properties management (description, label)
   - Collections (`/sources/source-collections`)

3. **`test_flows.py`** - Flow management endpoints
   - CRUD operations (`/flows`)
   - Batch operations (`/flows/batch`)
   - Tags management (`/flows/{id}/tags`)
   - Properties management (description, label, read_only)
   - Flow collection (`/flows/{id}/flow_collection`)
   - Bit rate operations (max_bit_rate, avg_bit_rate)
   - Storage allocation (`/flows/{id}/storage`)

4. **`test_segments.py`** - Flow segment endpoints
   - CRUD operations (`/flows/{id}/segments`)
   - Time range queries
   - Pagination
   - Storage operations
   - Batch operations

5. **`test_objects.py`** - Object management endpoints
   - Object information (`/objects/{id}`)
   - Upload URL validation
   - Object metadata
   - Upload workflow testing
   - Content validation
   - Object deletion

6. **`test_analytics.py`** - Analytics endpoints
   - Flow usage analytics (`/analytics/flow-usage`)
   - Storage usage analytics (`/analytics/storage-usage`)
   - Time range analysis (`/analytics/time-range-analysis`)
   - Performance testing
   - Data consistency validation

7. **`test_webhooks.py`** - Webhook management endpoints
   - Webhook CRUD (`/service/webhooks`)
   - Webhook configuration
   - Validation testing
   - Performance testing

8. **`test_deletion_requests.py`** - Deletion request endpoints
   - Deletion request CRUD (`/flow-delete-requests`)
   - Cascade deletion testing
   - Dependency violation handling
   - Batch deletion operations

## Running Tests

### Run All Tests
```bash
cd /Users/jesse.thaloor/Developer/github/bbctams/tests/test_endpoints
python test_runner.py
```

### Run Specific Test Modules
```bash
# Run only core service tests
python test_runner.py core

# Run multiple specific modules
python test_runner.py sources flows objects

# Available modules: core, sources, flows, segments, objects, analytics, webhooks, deletion
```

### Run Individual Test Modules
```bash
# Run individual test files
python test_core_service.py
python test_sources.py
python test_flows.py
# ... etc
```

## Test Features

### Comprehensive Coverage
- **All TAMS API 7.0 endpoints** are covered
- **All HTTP methods** (GET, POST, PUT, DELETE, HEAD) are tested
- **Error cases** and edge conditions are validated
- **Performance testing** is included for critical endpoints

### Robust Testing
- **Proper assertions** for all test cases
- **Error handling** with appropriate status code validation
- **Data cleanup** after each test module
- **Real data testing** with actual API interactions

### Organized Structure
- **Modular design** for easy maintenance
- **Shared utilities** to avoid code duplication
- **Clear separation** of concerns
- **Comprehensive logging** and result reporting

## Test Data Management

The tests use a shared `test_data` dictionary to track created resources and ensure proper cleanup:

```python
test_data = {
    "source_id": None,
    "flow_id": None,
    "object_ids": [],
    "segment_ids": [],
    "collection_ids": []
}
```

Each test module cleans up its data after completion to avoid conflicts between test runs.

## Error Handling

Tests are designed to handle various response scenarios:
- **Success cases** (200, 201, 204)
- **Expected errors** (400, 404, 409, 422, 500)
- **Graceful degradation** for unimplemented features
- **Proper validation** of error responses

## Performance Considerations

- **Response time monitoring** for critical endpoints
- **Batch operation testing** for efficiency
- **Resource cleanup** to prevent memory leaks
- **Concurrent request handling** validation

## Integration with TAMS API

The tests are designed to work with the actual TAMS API implementation:
- **Real HTTP requests** to the running API server
- **Proper authentication** handling (if required)
- **Schema validation** against TAMS 7.0 specification
- **End-to-end workflow** testing

## Maintenance

To add new tests or modify existing ones:

1. **Follow the existing patterns** in the test files
2. **Use shared utilities** from `test_utils.py`
3. **Add proper cleanup** for any created resources
4. **Include error case testing** for robustness
5. **Update this README** if adding new test modules

## Dependencies

- `requests` - HTTP client for API testing
- `datetime` - Time handling for test reporting
- Standard Python libraries only

## Notes

- Tests assume the TAMS API server is running on `http://localhost:8000`
- Tests are designed to be **idempotent** - they can be run multiple times safely
- **Resource cleanup** is automatic after each test module
- **Comprehensive logging** provides detailed test execution information
