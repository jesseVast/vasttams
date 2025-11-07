# Parallel Test Runner

## Overview

The `run_tests_parallel.py` script runs test sections (files) in parallel, with tests within each section also running in parallel using pytest-xdist.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Main Process (run_tests_parallel.py)                  │
│  └─ ProcessPoolExecutor                                 │
│     ├─ Process 1: flows/test_router_comprehensive.py   │
│     │  └─ pytest-xdist (workers: auto)                │
│     ├─ Process 2: sources/test_router_comprehensive.py │
│     │  └─ pytest-xdist (workers: auto)                │
│     ├─ Process 3: segments/test_router_comprehensive.py│
│     │  └─ pytest-xdist (workers: auto)                │
│     └─ ... (more processes)                            │
└─────────────────────────────────────────────────────────┘
```

## Usage

### Basic Usage

Run all default router comprehensive tests:

```bash
cd /Users/jesse.thaloor/Developer/github/bbctams
python tests/run_tests_parallel.py
```

### Run Specific Test Files

```bash
python tests/run_tests_parallel.py tests/flows/test_router_comprehensive.py tests/analytics/test_router.py
```

### Customize Parallel Execution

```bash
# Limit number of test files running in parallel
python tests/run_tests_parallel.py --max-workers 4

# Set number of workers per test file
python tests/run_tests_parallel.py --file-workers 4

# Both options
python tests/run_tests_parallel.py --max-workers 4 --file-workers 2
```

### With Coverage

```bash
python tests/run_tests_parallel.py --coverage
```

## Command Line Options

- `test_files`: Test files to run (default: all router comprehensive tests)
- `--max-workers`: Maximum number of test files to run in parallel (default: auto = CPU count)
- `--file-workers`: Number of pytest-xdist workers per test file (default: auto)
- `--coverage`: Run with coverage reporting

## Examples

### Run All Router Tests

```bash
python tests/run_tests_parallel.py
```

### Run Specific Test Sections

```bash
python tests/run_tests_parallel.py \
    tests/flows/test_router_comprehensive.py \
    tests/sources/test_router_comprehensive.py \
    tests/segments/test_router_comprehensive.py
```

### Run with Limited Parallelism

```bash
# Run 2 test files at a time, 2 workers per file
python tests/run_tests_parallel.py --max-workers 2 --file-workers 2
```

## Output

The script provides:
- Real-time progress updates as each test file completes
- Summary of passed/failed test files
- Total execution time
- Error messages for failed tests

## Requirements

- Python 3.12+
- pytest
- pytest-xdist
- Server must be running (tests will skip if API unavailable)

## Notes

- Each test file runs in its own process for isolation
- Tests within each file run in parallel using pytest-xdist
- Default timeout: 10 minutes per test file
- Uses `/Users/jesse.thaloor/Developer/python/vasttams/bin/python` by default

