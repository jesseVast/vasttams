# TAMS Quick Start Guide

## Installation

```bash
# Development mode (editable)
pip install -e ".[dev]"

# Production mode
pip install .
```

## Running the Service

```bash
# Using uvicorn (recommended)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Using entry point (after installation)
tams

# Using Python module
python -m app.main

# Using run.py script
python run.py
```

## Quick Test

```bash
# Start the service
uvicorn app.main:app --reload

# In another terminal, test the health endpoint
curl http://localhost:8000/

# Test service info endpoint
curl http://localhost:8000/service
```

## Package Building

```bash
# Build distribution packages
python setup.py sdist bdist_wheel

# Install from built package
pip install dist/tams-8.0.0-py3-none-any.whl
```

## Module Usage

After installation, import and use:

```python
from app import main  # FastAPI app
from app.core.config import get_settings
from app.common.models import Tags
from app.flows.service import FlowStorageService
```

## Docker (Alternative)

```bash
docker build -f docker/server/Dockerfile -t tams:8.0.0 .
docker run -p 8000:8000 tams:8.0.0
```

See PACKAGING_GUIDE.md for detailed instructions.
