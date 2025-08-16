# Mock Tests Directory

This directory contains **unit tests** that use mocks, patches, and don't require real external services. These tests focus on testing individual components in isolation and can run quickly without external dependencies.

## Purpose

- **Fast Execution**: Tests run quickly without waiting for external services
- **Isolated Testing**: Each component is tested independently
- **CI/CD Friendly**: Can run in any environment without external dependencies
- **Development Speed**: Immediate feedback during development

## Test Categories

### Core Component Tests
- **VastDBManager Tests**: Database manager functionality with mocked connections
- **S3 Store Tests**: Storage layer with mocked S3 client
- **Auth Tests**: Authentication system with mocked providers
- **Manager Tests**: Business logic managers (Source, Flow, Segment, Object)

### Utility Tests
- **Column Management**: Table schema operations
- **Data Operations**: Insert, update, delete operations
- **Query Tests**: Query building and execution
- **Performance Tests**: Optimization and stress testing with mocked data

## Running Tests

```bash
# Run all mock tests
pytest mock_tests/ -v

# Run specific test category
pytest mock_tests/test_vastdbmanager*.py -v

# Run with coverage
pytest mock_tests/ --cov=app --cov-report=html
```

## Test Patterns

All tests in this directory follow these patterns:
- Use `unittest.mock` or `pytest-mock` for mocking
- No real database connections
- No real S3 operations
- No real HTTP requests
- Fast execution (< 1 second per test)

## File Naming Convention

- `test_*.py`: Standard test files
- `test_*_simple.py`: Simplified test versions
- `test_*_stress.py`: Performance and load testing
- `example_*.py`: Usage examples and demonstrations
