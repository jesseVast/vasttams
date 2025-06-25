# TAMS Tests

This directory contains all test files for the TAMS (Time-addressable Media Store) API application.

## Test Files Overview

### Core Test Files

#### `test_basic.py`
- **Purpose**: Basic functionality tests for the TAMS API
- **Coverage**: Core API endpoints, request/response validation, error handling
- **Dependencies**: FastAPI, pytest, httpx
- **Usage**: Tests the main API functionality including sources, flows, and segments

#### `test_vast_store.py`
- **Purpose**: Unit tests for the VASTStore class
- **Coverage**: VAST database operations, S3 storage integration, data model conversions
- **Dependencies**: VAST database, S3 storage, PyArrow
- **Usage**: Tests the high-level store interface that combines VAST DB and S3

#### `test_vastdbmanager.py`
- **Purpose**: Unit tests for the VastDBManager class
- **Coverage**: Database connection, table operations, CRUD operations, query optimization
- **Dependencies**: VAST database, PyArrow, ibis
- **Usage**: Tests the low-level VAST database management functionality

### Example and Documentation

#### `example_vastdbmanager_usage.py`
- **Purpose**: Example usage demonstration for VastDBManager
- **Coverage**: Common usage patterns, best practices, error handling examples
- **Dependencies**: VAST database, PyArrow
- **Usage**: Demonstrates how to use the VastDBManager class effectively

## Running Tests

### Prerequisites
Make sure you have the required dependencies installed:
```bash
pip install -r requirements.txt
```

### Running All Tests
```bash
# From the project root
python -m pytest tests/

# With verbose output
python -m pytest tests/ -v

# With coverage
python -m pytest tests/ --cov=app --cov-report=html
```

### Running Specific Test Files
```bash
# Run only basic tests
python -m pytest tests/test_basic.py

# Run only VAST store tests
python -m pytest tests/test_vast_store.py

# Run only database manager tests
python -m pytest tests/test_vastdbmanager.py
```

### Running Specific Test Functions
```bash
# Run a specific test function
python -m pytest tests/test_vastdbmanager.py::test_create_table

# Run tests matching a pattern
python -m pytest tests/ -k "create"
```

## Test Configuration

### Environment Setup
Tests may require specific environment variables or configuration:
- `VAST_ENDPOINT`: VAST database endpoint
- `VAST_ACCESS_KEY`: VAST access key
- `VAST_SECRET_KEY`: VAST secret key
- `S3_ENDPOINT_URL`: S3-compatible storage endpoint
- `S3_ACCESS_KEY_ID`: S3 access key
- `S3_SECRET_ACCESS_KEY`: S3 secret key

### Mock Configuration
Some tests use mocks to avoid requiring actual database or storage connections:
- Database operations are mocked in unit tests
- S3 operations are mocked for isolated testing
- Network calls are mocked for API tests

## Test Structure

### Unit Tests
- **Location**: Individual test files
- **Scope**: Single module or class functionality
- **Dependencies**: Minimal, often mocked
- **Speed**: Fast execution

### Integration Tests
- **Location**: `test_basic.py`
- **Scope**: End-to-end API functionality
- **Dependencies**: Full application stack
- **Speed**: Slower, requires setup

### Example Tests
- **Location**: `example_vastdbmanager_usage.py`
- **Scope**: Usage demonstration and documentation
- **Dependencies**: Actual VAST database
- **Speed**: Variable, depends on database

## Writing New Tests

### Test File Naming
- Use `test_*.py` naming convention
- Include the module name being tested
- Example: `test_vast_store.py` for testing `vast_store.py`

### Test Function Naming
- Use descriptive names that explain what is being tested
- Follow pattern: `test_<functionality>_<scenario>`
- Example: `test_create_source_success()`, `test_create_source_invalid_data()`

### Test Structure
```python
def test_functionality_scenario():
    """Test description explaining what is being tested"""
    # Arrange - Set up test data and conditions
    test_data = {...}
    
    # Act - Execute the functionality being tested
    result = function_under_test(test_data)
    
    # Assert - Verify the expected outcome
    assert result is not None
    assert result.status == "success"
```

### Best Practices
1. **Isolation**: Each test should be independent
2. **Cleanup**: Clean up any test data or resources
3. **Mocking**: Use mocks for external dependencies
4. **Documentation**: Include clear docstrings
5. **Assertions**: Use specific, meaningful assertions

## Troubleshooting

### Common Issues

#### Import Errors
If you encounter import errors, ensure you're running tests from the project root:
```bash
cd /path/to/bbctams
python -m pytest tests/
```

#### Database Connection Issues
For tests requiring actual database connections:
1. Ensure VAST database is running
2. Check environment variables are set correctly
3. Verify network connectivity to database endpoint

#### S3 Connection Issues
For tests requiring S3 storage:
1. Ensure S3-compatible storage is running (e.g., MinIO)
2. Check S3 credentials and endpoint configuration
3. Verify bucket exists and is accessible

### Debug Mode
Run tests with debug output:
```bash
python -m pytest tests/ -v -s --tb=long
```

## Contributing

When adding new tests:
1. Follow the existing naming conventions
2. Include proper docstrings and comments
3. Use appropriate mocking for external dependencies
4. Ensure tests are fast and reliable
5. Update this README if adding new test categories

## Test Coverage

Current test coverage includes:
- ✅ Core API endpoints
- ✅ VAST database operations
- ✅ S3 storage operations
- ✅ Data model validation
- ✅ Error handling scenarios
- ✅ Integration workflows

Areas for improvement:
- 🔄 Performance testing
- 🔄 Load testing
- 🔄 Security testing
- 🔄 End-to-end user workflows 