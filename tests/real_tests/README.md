# Real Tests Directory

This directory contains **integration tests** that require real external services such as databases, S3 storage, or running API servers. These tests validate end-to-end functionality and can be used for performance testing.

## Purpose

- **End-to-End Validation**: Tests complete workflows from API to storage
- **Real Performance**: Measures actual performance with real services
- **Production Validation**: Ensures compatibility with production environments
- **Integration Verification**: Validates component interactions

## Test Categories

### API Integration Tests
- **Basic API Tests**: Core endpoint functionality with running server
- **Docker Deployment**: Container deployment and service validation
- **Webhook Tests**: Real webhook delivery and processing

### Database Integration Tests
- **Real Database Tests**: VAST database operations with actual data
- **S3 Integration**: Real S3 storage operations and presigned URLs
- **Data Flow Tests**: Complete data ingestion and retrieval workflows

### Utility Scripts
- **Database Cleanup**: Scripts for test data cleanup
- **Integration Runners**: Test orchestration and reporting

## Prerequisites

Before running these tests, ensure:

1. **VAST Database**: Running and accessible
2. **S3 Storage**: Configured and accessible
3. **TAMS API Server**: Running on expected port
4. **Environment Variables**: Properly configured
5. **Network Access**: All services reachable

## Running Tests

```bash
# Run all real tests (requires services to be running)
pytest real_tests/ -v

# Run specific test category
pytest real_tests/test_*.py -v

# Run with real database
pytest real_tests/test_integration_real_db.py -v

# Run Docker deployment tests
pytest real_tests/test_docker_deployment.py -v
```

## Test Patterns

All tests in this directory:
- Connect to real external services
- May take longer to execute
- Require proper environment setup
- Can fail due to external service issues
- Provide real performance metrics

## File Descriptions

- `test_basic.py`: Core API functionality tests
- `test_docker_deployment.py`: Docker container validation
- `test_integration_real_db.py`: Comprehensive database integration
- `test_s3_store_real_endpoint.py`: S3 storage integration
- `test_webhook_ownership.py`: Webhook functionality validation
- `integration_test.py`: End-to-end workflow tests
- `run_integration_tests.py`: Test orchestration script
- `drop_all_tables.py`: Database cleanup utility

## Environment Setup

```bash
# Set required environment variables
export VAST_ENDPOINT="http://your-vast-server"
export VAST_ACCESS_KEY="your-access-key"
export VAST_SECRET_KEY="your-secret-key"
export S3_ENDPOINT_URL="http://your-s3-server"
export S3_ACCESS_KEY_ID="your-s3-key"
export S3_SECRET_ACCESS_KEY="your-s3-secret"

# Start TAMS API server
python run.py

# Run tests
pytest real_tests/ -v
```
