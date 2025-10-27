# Python Package Import Strategy

## Current State

The codebase uses **relative imports** throughout, which is appropriate for a Python package. The imports follow this pattern:

- Within the same module: `.module_name`
- Up one level: `..parent_module`
- Up two levels: `...grandparent_module`

## Issues Fixed

1. ✅ Changed `app.models` imports to relative imports in:
   - `app/core/event_manager.py`
   - `app/core/tams_logging.py`
   - `app/auth/providers/basic.py`

2. ✅ Updated `app.core.config` imports to relative imports

## Package Structure

```
app/
├── __init__.py                    # Package initialization
├── main.py                        # Main FastAPI app
├── common/                        # Shared code
│   ├── __init__.py
│   ├── models.py                  # Shared models
│   ├── filters.py                 # Shared filters
│   ├── responses.py               # Shared response models
│   ├── storage/                   # Storage infrastructure
│   │   ├── __init__.py
│   │   ├── schemas.py              # Schema registry
│   │   ├── dependencies.py
│   │   ├── interfaces.py
│   │   ├── main_service.py
│   │   ├── table_initializer.py
│   │   └── timestamp_utils.py
│   └── tags/                      # Tag services
│       ├── __init__.py
│       ├── schemas.py
│       ├── service.py
│       ├── manager.py
│       └── http_service.py
├── core/                          # Core infrastructure
│   ├── __init__.py
│   ├── config.py
│   ├── dependencies.py
│   ├── utils.py
│   ├── telemetry.py
│   ├── event_manager.py
│   ├── tams_logging.py
│   ├── tams_errors.py
│   ├── simple_logging.py
│   └── timerange_utils.py
├── flows/                         # Flow resource
│   ├── __init__.py
│   ├── models.py
│   ├── router.py
│   ├── schemas.py
│   └── service.py
├── sources/                       # Source resource
│   ├── __init__.py
│   ├── models.py
│   ├── router.py
│   ├── schemas.py
│   └── service.py
├── objects/                       # Object resource
│   ├── __init__.py
│   ├── models.py
│   ├── router.py
│   ├── schemas.py
│   └── service.py
├── segments/                      # Segment resource
│   ├── __init__.py
│   ├── models.py
│   ├── router.py
│   ├── schemas.py
│   └── service.py
├── service/                      # Service operations
│   ├── __init__.py
│   ├── models.py
│   ├── router.py
│   ├── deletion_router.py
│   ├── webhooks.py
│   ├── storage_models.py
│   └── schemas.py
├── auth/                          # Authentication
│   ├── __init__.py
│   ├── router.py
│   ├── core.py
│   ├── middleware.py
│   ├── models.py
│   ├── dependencies.py
│   ├── service.py
│   ├── provider_config.py
│   ├── schemas.py
│   └── providers/
│       ├── __init__.py
│       ├── base.py
│       ├── basic.py
│       ├── jwt.py
│       └── url_token.py
└── models/                        # Legacy models
    ├── __init__.py
    ├── core.py
    ├── models.py
    ├── legacy.py
    └── filters.py
```

## Import Patterns

### Within Module (Same Directory)
```python
from .module_name import ClassName
```

### Up One Level
```python
from ..parent_module import Something
```

### Up Two Levels
```python
from ...grandparent_module import Something
```

## Working Examples

### From `app/flows/service.py` to `app/common/models.py`:
```python
from ...common.models import Tags, TimeRange
```

### From `app/common/storage/main_service.py` to `app/flows/service.py`:
```python
from ...flows.service import FlowStorageService
```

### From `app/core/utils.py` to `app/common/models.py`:
```python
from ..common.models import Tags
```

## Entry Point

The main application entry point is:
- `app/main.py` - FastAPI application
- `app/__init__.py` - Package definition with metadata

## Running as a Module

The app can be run as:
```bash
# Direct execution
python -m app.main

# Or via uvicorn
uvicorn app.main:app

# Or via run.py
python run.py
```

## Package Installation

When installed as a package:
```bash
pip install -e .

# Then imports work like:
from app import main
from app.common.models import Tags
from app.flows.service import FlowStorageService
```

This structure supports:
1. **Relative imports** - Works when running as part of the package
2. **Absolute imports** - Works when installed as a package
3. **Development mode** - Running directly from source

