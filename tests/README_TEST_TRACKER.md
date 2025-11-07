# Test Tracker System

The test tracker automatically skips tests that have passed previously and whose code hasn't changed, significantly speeding up test runs.

## How It Works

1. **First Run**: All tests run normally
2. **Subsequent Runs**: 
   - Tests that passed previously are checked against their source files
   - If source files haven't changed, tests are skipped
   - If source files changed, tests are re-run
   - Tests that failed previously are always re-run

## Usage

### Normal Usage

Just run pytest as usual - the tracker works automatically:

```bash
pytest tests/
```

The tracker will:
- Skip tests that passed and code hasn't changed
- Run tests that failed previously
- Run tests for code that changed
- Show statistics at the end

### Disable Tracker

To run all tests regardless of cache:

```bash
pytest tests/ --no-test-tracker
```

### Force Run Specific Test

Mark a test to always run:

```python
@pytest.mark.always_run
def test_critical_feature():
    ...
```

### Manage Cache

View statistics:
```bash
python tests/manage_test_tracker.py stats
```

List all tracked tests:
```bash
python tests/manage_test_tracker.py list
```

Clear cache (force all tests to run next time):
```bash
python tests/manage_test_tracker.py clear
```

## Cache Location

The cache is stored at:
```
.pytest_cache/test_tracker.json
```

## How Source Files Are Mapped

The tracker automatically maps test files to source files:

- `tests/flows/test_router_comprehensive.py` → `src/vasttams/flows/router.py`
- `tests/flows/test_service.py` → `src/vasttams/flows/service.py`
- `tests/auth/test_rbac.py` → `src/vasttams/auth/rbac.py`
- `tests/core/test_errors.py` → `src/vasttams/core/tams_errors.py`

The tracker also tracks:
- The test file itself (if test changes, re-run it)
- All Python files in the corresponding source module directory

## Benefits

- **Faster test runs**: Skip unchanged tests
- **Focus on failures**: Always re-run failed tests
- **Automatic**: No configuration needed
- **Safe**: Always runs tests for changed code

## Example Output

```
⏭️  Skipping 245 tests (passed previously, code unchanged)

======================== test session starts =========================
collected 845 items
skipped 245 items
running 600 items

... (test output) ...

📊 Test Tracker Stats:
   Passed (cached): 245
   Failed (tracked): 5
   Total tracked: 250
```

## Notes

- The tracker uses file hashes to detect changes
- Tests are tracked by their full nodeid (e.g., `tests/flows/test_router.py::TestClass::test_method`)
- Failed tests are always re-run until they pass
- The cache persists between test runs

