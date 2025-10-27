# TAMS FastAPI Service Packaging Guide

## Overview

The TAMS application is packaged as a Python module that can be:
1. **Installed as a package** via `pip install`
2. **Run as a service** using `uvicorn`
3. **Integrated** into other Python applications

## Package Structure

```
tams/
├── setup.py                  # Package setup configuration
├── pyproject.toml            # Modern Python packaging config
├── MANIFEST.in               # Files to include in package
├── app/                      # Main application package
│   ├── __init__.py          # Package initialization
│   ├── main.py               # FastAPI application entry point
│   ├── core/                 # Core infrastructure
│   ├── common/               # Shared code
│   ├── flows/                # Flow resource
│   ├── sources/              # Source resource
│   ├── objects/              # Object resource
│   ├── segments/             # Segment resource
│   ├── service/              # Service operations
│   └── auth/                 # Authentication
└── README.md                 # Package documentation
```

## Installation

### Development Installation

```bash
# Install in editable mode for development
pip install -e .

# Or with development dependencies
pip install -e ".[dev]"
```

### Production Installation

```bash
# From source
pip install .

# Or install dependencies separately
pip install -r requirements-prod.txt
pip install .
```

## Running the Service

### Option 1: Using Uvicorn (Recommended)

```bash
# Development mode with auto-reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production mode
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Option 2: Using Python Module

```bash
# Direct Python execution
python -m app.main

# Or use the entry point (after installation)
tams
```

### Option 3: Using run.py

```bash
# Run from project root
python run.py
```

## Packaging for Distribution

### Build Source Distribution

```bash
# Build source distribution
python setup.py sdist

# Build wheel distribution
python setup.py bdist_wheel

# Build both
python setup.py sdist bdist_wheel
```

### Build Output

The build process creates:
- `dist/tams-8.0.0.tar.gz` - Source distribution
- `dist/tams-8.0.0-py3-none-any.whl` - Wheel distribution

### Installing from Built Packages

```bash
# From source distribution
pip install dist/tams-8.0.0.tar.gz

# From wheel
pip install dist/tams-8.0.0-py3-none-any.whl
```

## Docker Packaging

The service can also be packaged in Docker:

```bash
# Build Docker image
docker build -f docker/Dockerfile -t tams:8.0.0 .

# Run container
docker run -p 8000:8000 tams:8.0.0
```

## Integration with Other Applications

### As a Library

Install the package and import modules:

```python
from app import main
from app.core.config import get_settings
from app.common.models import Tags, TimeRange
from app.flows.service import FlowStorageService
```

### As a FastAPI Mount

Mount the TAMS app in another FastAPI application:

```python
from fastapi import FastAPI
from app.main import app as tams_app

app = FastAPI()
app.mount("/tams", tams_app)
```

## Configuration

The package requires configuration via environment variables or `.env` file:

```bash
# Core settings
VAST_STORE_URL=
S3_ENDPOINT_URL=
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=

# Application settings
ENABLE_TABLE_PROJECTIONS=true
ASYNC_DELETION_THRESHOLD=100
```

## Testing

```bash
# Run tests
pytest

# With coverage
pytest --cov=app

# Specific test file
pytest tests/test_endpoints/test_flows.py
```

## Development Workflow

1. **Install in editable mode**:
   ```bash
   pip install -e ".[dev]"
   ```

2. **Make code changes**:
   - Edit files in `app/`
   - Changes are immediately available (no reinstall needed)

3. **Test changes**:
   ```bash
   pytest
   ```

4. **Package and distribute**:
   ```bash
   python setup.py sdist bdist_wheel
   ```

## Module Structure

### Entry Points

The package defines console scripts in `setup.py`:

```python
entry_points={
    "console_scripts": [
        "tams=app.main:main",
    ],
}
```

This creates a `tams` command that can be run after installation.

### Package Exports

Key modules are exported from the package `__init__.py`:

```python
from app import main            # Main FastAPI app
from app.core import get_settings
from app.common.models import Tags
```

## Troubleshooting

### Import Errors

If you see import errors after installation:

1. **Check Python path**: Ensure `app/` is in Python path
2. **Reinstall**: Run `pip install -e .` to reinstall in editable mode
3. **Check virtual environment**: Ensure you're in the correct virtualenv

### Module Not Found

If modules are not found:

1. **Verify installation**: Run `pip list | grep tams`
2. **Check package location**: Run `python -c "import app; print(app.__file__)"`

### FastAPI App Not Loading

If the app doesn't start:

1. **Check dependencies**: Run `pip install -r requirements.txt`
2. **Check configuration**: Ensure `.env` file is configured
3. **Check logs**: Look at logs for error messages

## Best Practices

1. **Always use virtual environments** for development and production
2. **Install in editable mode** during development (`pip install -e .`)
3. **Use version pinning** in production requirements
4. **Test the package** after building with `pip install dist/tams-*.whl`
5. **Document changes** in CHANGELOG.md when creating releases

## Publishing to PyPI (Optional)

If you want to publish to PyPI:

```bash
# Build packages
python setup.py sdist bdist_wheel

# Upload to PyPI (test)
twine upload --repository testpypi dist/*

# Upload to PyPI (production)
twine upload dist/*
```

## Summary

The TAMS package is now ready to be:
- ✅ Installed as a Python package
- ✅ Run as a FastAPI service
- ✅ Integrated into other applications
- ✅ Packaged for distribution
- ✅ Used in Docker containers

All imports use relative paths, making the package portable and installable anywhere.

