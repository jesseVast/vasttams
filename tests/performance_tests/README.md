# Performance Tests Module

This module contains performance and stress tests for the TAMS system. These tests are separate from integration tests and focus on:

## Test Categories

### 1. Performance Tests (`TestPerformanceReal`)
- **S3 Store Initialization Performance**: Tests S3 store setup time
- **VastDBManager Initialization Performance**: Tests database manager setup time
- **S3 Segment Storage Performance**: Tests segment upload/download performance
- **Table Operations Performance**: Tests database table operations speed
- **Data Operations Performance**: Tests CRUD operation performance
- **Concurrent Operations Performance**: Tests parallel operation handling
- **Memory Usage Performance**: Tests memory consumption patterns
- **Cleanup Performance**: Tests cleanup operation efficiency

### 2. Stress Tests (`TestStressReal`)
- **Concurrent S3 Operations**: Tests multiple simultaneous S3 operations
- **Concurrent VastDBManager Operations**: Tests parallel database operations
- **Large Data Handling**: Tests system behavior with large datasets
- **Memory Usage Under Load**: Tests memory management under stress
- **Resource Cleanup**: Tests cleanup efficiency under load

### 3. Scalability Tests (`TestScalabilityReal`)
- **Scalable Segment Operations**: Tests segment handling at scale
- **Scalable Database Operations**: Tests database performance at scale

## Usage

### Run All Performance Tests
```bash
python tests/run_performance_tests.py
```

### Run Specific Test Categories
```bash
# Fast performance tests only
python tests/run_performance_tests.py --fast

# Stress tests only
python tests/run_performance_tests.py --stress

# Scalability tests only
python tests/run_performance_tests.py --scalability
```

### Run with Verbose Output
```bash
python tests/run_performance_tests.py --verbose
```

### Run with Coverage
```bash
python tests/run_performance_tests.py --coverage
```

## Test Configuration

Performance tests use realistic thresholds:
- **Initialization**: < 5 seconds
- **Operations**: < 20 seconds
- **Memory**: < 500MB peak usage
- **Concurrent**: < 30 seconds for 10 parallel operations

## Dependencies

- Real VAST database connection
- Real S3 storage backend
- Server running on localhost:8000
- Clean database state (recommended)

## Notes

- These tests are resource-intensive and may take several minutes
- They require a running TAMS server with real backend services
- Performance results may vary based on system resources and network conditions
- Tests include cleanup operations to maintain database integrity
