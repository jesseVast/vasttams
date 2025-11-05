# Parallel Test Execution

Tests can now run in parallel using `pytest-xdist` for much faster execution.

## Quick Start

Run tests in parallel with auto-detected number of workers:
```bash
pytest -n auto
```

Run with specific number of workers:
```bash
pytest -n 4  # Use 4 parallel workers
```

## Why Parallel Execution Works

1. **Unique IDs**: Tests use UUIDs for all resources (sources, flows, segments, objects), preventing conflicts
2. **Session-scoped fixtures**: `auth_headers` fixture is session-scoped and works fine with parallel execution
3. **Shared API server**: The API server handles concurrent requests properly
4. **Database isolation**: Tests create unique resources and clean up after themselves

## Considerations

### Tests that might need serial execution

Some tests might need to run serially if they:
- Depend on specific ordering
- Share global state
- Clean up shared resources

Mark these tests with `@pytest.mark.serial`:
```python
@pytest.mark.serial
def test_that_needs_serial_execution():
    ...
```

Then run with:
```bash
pytest -n auto -m "not serial"  # Run parallel tests
pytest -m serial                 # Run serial tests separately
```

### Performance

Parallel execution typically provides:
- **3-4x speedup** on 4-core machines
- **6-8x speedup** on 8-core machines
- Scales with CPU cores (up to reasonable limits)

### Coverage with Parallel Execution

When running with coverage, use `pytest-cov` which supports parallel execution:
```bash
pytest -n auto --cov=src/vasttams --cov-report=html
```

## Troubleshooting

If tests fail in parallel but pass serially:
1. Check for resource conflicts (same IDs, shared state)
2. Verify cleanup is working correctly
3. Check for race conditions in test setup/teardown
4. Consider marking problematic tests with `@pytest.mark.serial`


