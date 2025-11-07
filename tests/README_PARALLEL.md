# Fast Parallel Test Execution

Tests are now configured to run in parallel by default for much faster execution.

## Quick Start

Simply run pytest as normal - parallel execution is enabled automatically:

```bash
pytest tests/
```

Or use the fast test runner script:

```bash
./tests/run_tests_fast.sh
```

## Performance Improvements

- **3-4x faster** on 4-core machines
- **6-8x faster** on 8-core machines  
- **Scales with CPU cores** (up to reasonable limits)

## Configuration

Parallel execution is configured in `tests/pytest.ini`:

- `-n auto` - Automatically detects number of CPU cores
- `--dist=loadscope` - Distributes tests by class/module scope for better isolation
- `--maxfail=10` - Stops after 10 failures (prevents long runs with many failures)

## Optimizations Applied

1. **Parallel execution enabled by default** - All tests run in parallel
2. **Reduced retry delays** - Auth fixture retries faster (1s instead of 2s)
3. **Fewer retries** - Auth fixture uses 3 retries instead of 5
4. **Load scope distribution** - Tests grouped by class/module for better isolation
5. **Session-scoped fixtures** - Shared fixtures (auth_headers) work efficiently with parallel execution

## Running Specific Tests

Run specific test files or patterns:

```bash
# Single file
pytest tests/flows/test_router_comprehensive.py

# Multiple files
pytest tests/flows/ tests/sources/

# Specific test
pytest tests/flows/test_router_comprehensive.py::TestFlowsRouterGET::test_list_flows
```

## Disabling Parallel Execution

If you need to run tests serially (for debugging):

```bash
pytest tests/ -n 0
```

Or temporarily disable in pytest.ini by removing `-n auto`.

## Troubleshooting

### Tests fail in parallel but pass serially

1. Check for resource conflicts (same IDs, shared state)
2. Verify cleanup is working correctly
3. Check for race conditions in test setup/teardown
4. Mark problematic tests with `@pytest.mark.serial`:

```python
@pytest.mark.serial
def test_that_needs_serial_execution():
    ...
```

Then run serial tests separately:
```bash
pytest -m serial
pytest -m "not serial"  # Run parallel tests
```

### Performance Issues

- If tests are still slow, check for:
  - Long-running fixtures
  - Network timeouts
  - Database connection pooling
  - API rate limiting

### Coverage with Parallel Execution

Coverage works with parallel execution:

```bash
pytest --cov=src/vasttams --cov-report=html
```

