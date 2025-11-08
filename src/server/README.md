# VastTAMS Server Package

This directory contains the VastTAMS server Python package (`vasttamsserver`) and all build configuration files.

## Directory Structure

```
src/server/
├── vasttamsserver/        # The main Python package
│   ├── __init__.py
│   ├── main.py            # FastAPI application
│   ├── auth/              # Authentication
│   ├── common/            # Shared utilities
│   ├── core/              # Core infrastructure
│   ├── flows/             # Flow resource
│   ├── objects/           # Object resource
│   ├── segments/          # Segment resource
│   ├── service/           # Service operations
│   └── sources/           # Source resource
├── setup.py               # Package setup configuration
├── pyproject.toml         # Modern Python packaging
├── MANIFEST.in            # Files to include in package
├── requirements.txt       # Production dependencies
└── requirements-dev.txt   # Development dependencies (includes production)
```

## Installation

⚠️ **Note**: This package requires private dependencies (`vastdbmanager` and `vasts3`) from a private GitLab repository. See [Private Dependencies Setup](../../docs/PRIVATE_DEPENDENCIES.md) for installation instructions.

### Development Installation

```bash
cd src/server
# First, configure GitLab authentication (see docs/PRIVATE_DEPENDENCIES.md)
pip install -e .
# Or install with dev dependencies:
pip install -r requirements-dev.txt
```

### Production Installation

```bash
cd src/server
# First, configure GitLab authentication (see docs/PRIVATE_DEPENDENCIES.md)
pip install .
# Or install production dependencies only:
pip install -r requirements.txt
```

### Using UV (Recommended)

```bash
cd src/server
uv pip install -e .
# For development with all dependencies:
uv pip install -r requirements-dev.txt
```

## Usage

After installation, you can import and use the package:

```python
from vasttamsserver import app
from vasttamsserver.core.config import get_settings
from vasttamsserver.flows.models import Flow
```

Or run the FastAPI application:

```bash
uvicorn vasttamsserver.main:app
```

Or use the provided entry point:

```bash
tams  # Runs the application
```

Or use the run scripts from the project root:

```bash
python run.py          # Production mode
python run_dev.py      # Development mode with auto-reload
```

## Package Structure

The package follows Python best practices:
- Source code in `vasttamsserver/`
- Build files at the same level
- `package_dir` set to "." for clean imports
- Absolute imports throughout (`vasttamsserver.*`)

## Dependencies

- **Production**: Install with `pip install -r requirements.txt`
- **Development**: Install with `pip install -r requirements-dev.txt` (includes production + test tools)

## Building Distribution Packages

```bash
cd src/server
python setup.py sdist bdist_wheel
```

This creates distribution packages in `dist/` directory.

## Package Name

The package is installed as `vasttamsserver` and can be imported as:
```python
import vasttamsserver
from vasttamsserver.main import app
```

