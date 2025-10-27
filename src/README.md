# VastTAMS Source Directory

This directory contains the VastTAMS Python package and all build configuration files.

## Directory Structure

```
src/
├── vasttams/              # The main Python package
│   ├── __init__.py
│   ├── main.py            # FastAPI application
│   ├── auth/              # Authentication
│   ├── common/            # Shared utilities
│   ├── core/              # Core infrastructure
│   ├── flows/             # Flow resource
│   ├── models/            # Legacy models
│   ├── objects/           # Object resource
│   ├── segments/          # Segment resource
│   ├── service/           # Service operations
│   └── sources/           # Source resource
├── setup.py               # Package setup configuration
├── pyproject.toml         # Modern Python packaging
├── MANIFEST.in            # Files to include in package
└── requirements.txt       # Python dependencies
```

## Installation

### Development Installation

```bash
cd src
pip install -e .
```

### Production Installation

```bash
cd src
pip install .
```

### Using UV (Recommended)

```bash
cd src
uv pip install -e .
```

## Usage

After installation, you can import and use the package:

```python
from vasttams import app
from vasttams.core.config import get_settings
from vasttams.flows.models import Flow
```

Or run the FastAPI application:

```bash
uvicorn vasttams.main:app
```

Or use the provided entry point:

```bash
tams  # Runs the application
```

## Package Structure

The package follows Python best practices:
- Source code in `vasttams/`
- Build files at the same level
- `package_dir` set to "." for clean imports
- Absolute imports throughout (`vasttams.*`)

## Building Distribution Packages

```bash
cd src
python setup.py sdist bdist_wheel
```

This creates distribution packages in `dist/` directory.

