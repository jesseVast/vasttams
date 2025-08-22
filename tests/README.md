# BBC TAMS Test Suite

## 🏗️ **NEW CONSOLIDATED TEST STRUCTURE**

### **Test Organization by APP Level Modules**

The test suite has been refactored to consolidate tests by application modules, reducing redundancy and improving maintainability.

```
tests/
├── conftest.py                 # Shared fixtures and mocks
├── test_auth/                  # Authentication module tests
│   ├── test_auth_core.py      # Core auth functionality
│   ├── test_auth_providers.py # Auth provider tests
│   └── test_auth_middleware.py # Auth middleware tests
├── test_storage/               # Storage module tests
│   ├── test_storage_core.py   # Core storage functionality
│   ├── test_s3_store.py       # S3 storage tests
│   ├── test_vast_store.py     # VAST storage tests
│   └── test_storage_endpoints.py # Storage endpoint tests
├── test_api/                   # API module tests
│   ├── test_api_routers.py    # API router tests
│   ├── test_api_flows.py      # Flows API tests
│   ├── test_api_objects.py    # Objects API tests
│   ├── test_api_segments.py   # Segments API tests
│   ├── test_api_sources.py    # Sources API tests
│   └── test_api_analytics.py  # Analytics API tests
├── test_core/                  # Core module tests
│   ├── test_config.py         # Configuration tests
│   ├── test_models.py         # Data model tests
│   └── test_utils.py          # Utility function tests
├── test_integration/           # Integration tests
│   ├── test_end_to_end_workflow.py # Full workflow test (with parameterized storage)
│   └── PARAMETERIZED_TESTING_GUIDE.md # Guide for implementing parameterized tests
└── test_utils/                 # Test utilities
    ├── mock_vastdbmanager.py  # Shared VASTDB manager mock
    ├── mock_s3store.py        # Shared S3 store mock
    └── test_helpers.py        # Common test helpers
```

### **Key Benefits of New Structure**

1. **Module-Based Organization**: Tests are organized by application modules (auth, storage, api, core)
2. **Shared Mocks**: Common mock implementations (VASTDBmanager, S3store) shared across all tests
3. **CRUD Coverage**: Each module includes comprehensive CRUD operation tests
4. **Reduced Redundancy**: Eliminated duplicate test files and consolidated similar functionality
5. **Better Maintainability**: Clear separation of concerns and easier test discovery
6. **Performance Tests Removed**: Focus on functional testing rather than performance

### **Test Categories**

#### **Unit Tests (Mock)**
- Use shared mock implementations for VASTDBmanager and S3store
- Test individual components in isolation
- Fast execution without external dependencies

#### **Integration Tests (Parameterized)**
- **Parameterized Storage Testing**: Same tests run against both mock and real storage
- **Easy Switching**: Environment variable controls storage backend (`TAMS_TEST_BACKEND=mock|real`)
- **Real Credentials**: Uses S3 and database credentials from config.py
- **No Code Duplication**: Single test file approach with automatic backend switching
- **End-to-End Workflow**: Complete workflow validation from source creation to analytics

#### **CRUD Tests**
- Create, Read, Update, Delete operations for each module
- Data validation and error handling
- Edge case coverage

### **Running Tests**

```bash
# Run all tests
python -m pytest tests/

# Run specific module tests
python -m pytest tests/test_auth/
python -m pytest tests/test_storage/
python -m pytest tests/test_api/

# Run integration tests only
python -m pytest tests/test_integration/

# Run parameterized tests with different storage backends
export TAMS_TEST_BACKEND=mock    # Use mock storage (fast)
export TAMS_TEST_BACKEND=real    # Use real storage (requires services)
python -m pytest tests/test_integration/ -v

# Run with coverage
python -m pytest --cov=app tests/
```

### **Running Tests Without Warnings**

To get clean test output without deprecation warnings:

```bash
# Option 1: Use --disable-warnings flag (recommended)
python -m pytest tests/test_core/ -v --disable-warnings

# Option 2: Set environment variable
PYTHONWARNINGS="ignore" python -m pytest tests/test_core/ -v

# Option 3: Use the consolidated test runner (automatically clean)
python tests/run_consolidated_tests.py

# Option 4: Run specific test without warnings
python -m pytest tests/test_core/test_models.py::TestObjectModel::test_object_referenced_flows_handling -v --disable-warnings

### **Parameterized Testing Guide**

For implementing parameterized storage testing in your own tests, see:
- **`tests/test_integration/PARAMETERIZED_TESTING_GUIDE.md`** - Complete implementation guide
- **`tests/test_integration/test_end_to_end_workflow.py`** - Working example

**Quick Start:**
```bash
# Add to your test file
import os
USE_MOCK_STORAGE = os.getenv("TAMS_TEST_BACKEND", "mock") == "mock"

# Replace storage initialization
if USE_MOCK_STORAGE:
    vast_storage = MockVastDBManager()
    s3_storage = MockS3Store()
else:
    # Real storage setup from config.py
    from app.storage.vastdbmanager import VastDBManager
    from app.storage.s3_store import S3Store
    # ... setup real storage

# Run with different backends
export TAMS_TEST_BACKEND=mock    # Mock storage
export TAMS_TEST_BACKEND=real    # Real storage
```

**Note**: The pytest.ini configuration includes `--disable-warnings` by default, but some warnings may still appear during import. The environment variable approach is most reliable.

### **Test Dependencies**

- **pytest**: Test framework
- **pytest-asyncio**: Async test support
- **pytest-cov**: Coverage reporting
- **unittest.mock**: Mocking framework

### **Mock Implementations**

The test suite uses shared mock implementations for:
- **VASTDBmanager**: Mocked VAST database operations
- **S3store**: Mocked S3 storage operations
- **Configuration**: Mocked settings and environment variables

These mocks ensure consistent behavior across all tests and eliminate the need for external dependencies during unit testing. 