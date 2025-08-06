#!/usr/bin/env python3
"""
Script to generate OpenAPI JSON specification from the TAMS FastAPI application.
This script creates a comprehensive OpenAPI specification that can be used by
the /docs and /redoc endpoints.
"""

import json
import os
import sys
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "app"))

try:
    from app.main import app
except ImportError:
    # Fallback for direct execution
    sys.path.insert(0, str(Path(__file__).parent))
    from app.main import app

def generate_openapi_json():
    """Generate OpenAPI JSON specification"""
    
    # Ensure the api directory exists
    api_dir = Path(__file__).parent / "api"
    api_dir.mkdir(exist_ok=True)
    
    # Generate the OpenAPI schema
    openapi_schema = app.openapi()
    
    # Write to file
    output_file = api_dir / "openapi.json"
    with open(output_file, 'w') as f:
        json.dump(openapi_schema, f, indent=2)
    
    print(f"OpenAPI specification generated: {output_file}")
    print(f"Schema contains {len(openapi_schema.get('paths', {}))} endpoints")
    
    return output_file

if __name__ == "__main__":
    generate_openapi_json() 