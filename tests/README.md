# TAMS Test Suite

This directory contains the comprehensive test suite for the TAMS API.

## Quick Start

### Run all tests (parallel execution enabled by default)
```bash
pytest tests/
```

### Run specific module
```bash
pytest tests/sources/ -v
```

### Run with coverage
```bash
pytest tests/ --cov=src/server/vasttamsserver --cov-report=html
```

### Run integration tests only
```bash
pytest tests/integration/ -v
```

### Run specific test script
```bash
python tests/scripts/ingest_test_data.py
```

## Test Structure

```
tests/
├── auth/              # Authentication and authorization tests
├── core/              # Core functionality tests (errors, logging, responses)
├── common/            # Common utilities and schemas tests
├── flows/             # Flow module tests
├── objects/           # Object module tests
├── segments/          # Segment module tests
├── sources/           # Source module tests
├── services/          # Service layer tests
├── schemas/           # Schema validation tests
├── main/              # Application setup tests
├── looprecorder/      # Loop recorder tests
├── integration/       # Integration tests (end-to-end workflows)
│   ├── test_examples.py
│   ├── test_object_lifecycle.py
│   ├── test_s3_upload_workflow.py
│   └── test_webhook_delivery.py
└── scripts/           # Test utility scripts
    ├── analyze_compliance_coverage.py
    ├── create_collections.py
    ├── generate_test_data.py
    ├── ingest_test_data.py
    ├── ingest_test_data_real.py
    ├── manage_test_tracker.py
    ├── register_webhook_all_events.py
    ├── run_webhook_tests.sh
    ├── webhook_test_server.py
    └── webhook_test_server_README.md
```

## Test Coverage

See `COVERAGE_TRACKING.md` for detailed coverage status and progress.

**Current Status:**
- ✅ All routers: 24.7%+ coverage (comprehensive tests added)
- ✅ All services: 80%+ coverage (all services exceed target)
- ✅ Auth module: 36.1%+ coverage (125+ tests)
- ✅ Schemas: 97.6%+ coverage (82 tests)
- ✅ Core/Common: 41.1%+ coverage
- ✅ Entry points: 50%+ coverage

## Parallel Execution

Tests run in parallel by default using `pytest-xdist`. Configuration is in `pytest.ini`.

## Test Tracker

The test tracker automatically skips tests that passed previously and whose code hasn't changed. See `README_TEST_TRACKER.md` for details.

## Utility Scripts

All utility scripts are located in `tests/scripts/`:

- `ingest_test_data.py` - Script to create test data (sources, flows, objects, segments)
- `ingest_test_data_real.py` - Real-world test data ingestion script
- `generate_test_data.py` - Generate comprehensive test data
- `create_collections.py` - Create flow and source collections from test data
- `webhook_test_server.py` - HTTP server for testing webhook events
- `register_webhook_all_events.py` - Register webhook for all events
- `run_webhook_tests.sh` - Convenience script to run webhook tests with server
- `manage_test_tracker.py` - Manage test tracker cache and run failed tests
- `analyze_compliance_coverage.py` - Analyze compliance test coverage against OpenAPI spec

## Integration Tests

Integration tests are located in `tests/integration/`:

- `test_examples.py` - Example usage tests
- `test_object_lifecycle.py` - End-to-end object lifecycle tests
- `test_s3_upload_workflow.py` - S3 upload workflow tests
- `test_webhook_delivery.py` - Webhook delivery integration tests

## Documentation

- `COVERAGE_TRACKING.md` - Current test coverage status and tracking
- `README_TEST_TRACKER.md` - Test tracker system documentation
- `webhook_test_server_README.md` - Webhook test server documentation
