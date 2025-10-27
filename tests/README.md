# TAMS Test Suite

This directory contains the test suite for the TAMS API.

## Directory Structure

```
tests/
├── sources/          # Source module tests
│   ├── test_models.py       # Unit tests for Source models
│   └── test_database.py     # Integration tests against database
├── flows/            # Flow module tests (TODO)
├── objects/          # Object module tests (TODO)
├── segments/         # Segment module tests (TODO)
└── conftest.py       # Shared pytest configuration
```

## Running Tests

### Run all tests
```bash
python -m pytest tests/ -v
```

### Run specific module
```bash
python -m pytest tests/sources/ -v
```

### Run only unit tests
```bash
python -m pytest tests/sources/test_models.py -v
```

### Run only integration tests
```bash
python -m pytest tests/sources/test_database.py -v
```

## Test Categories

### Unit Tests (`test_models.py`)
- Test Pydantic model validation
- Test filter objects
- No database connection required
- Fast execution

### Integration Tests (`test_database.py`)
- Test against running TAMS server
- Requires API server to be running
- Create and verify data in database
- Automatically skip if server is not available

## Running Integration Tests

1. Start the TAMS server:
```bash
PYTHONPATH=src python run.py
```

2. In another terminal, run the tests:
```bash
PYTHONPATH=src python -m pytest tests/sources/test_database.py -v
```

## Current Status

- ✅ Sources module: Unit tests + Database integration tests
- ⏳ Flows module: Pending
- ⏳ Objects module: Pending
- ⏳ Segments module: Pending

## Test Results

- Sources: 13/14 tests passing (1 tag test needs investigation)
