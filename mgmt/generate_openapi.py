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

# Add the src directory to the Python path
root_dir = os.path.abspath(str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(root_dir) / "src" / "server"))
sys.path.insert(0, root_dir)

# Change to root directory so config/config.yaml is found
# In container, config is at /etc/tams/config.yaml, in dev it's at config/config.yaml
# The Settings class handles this automatically
os.chdir(root_dir)

try:
    from vasttamsserver.main import app
except (ImportError, ValueError, Exception) as e:
    # Handle config errors during build (VAST endpoint not configured)
    error_msg = str(e)
    if "VAST endpoint is not configured" in error_msg or "ValueError" in str(type(e)):
        print("Warning: Skipping OpenAPI generation - configuration not available during build")
        print("OpenAPI spec will be generated at runtime when the application starts")
        sys.exit(0)
    # Fallback for direct execution
    sys.path.insert(0, str(Path(__file__).parent))
    try:
        from vasttamsserver.main import app
    except (ImportError, ValueError, Exception) as e2:
        error_msg2 = str(e2)
        if "VAST endpoint is not configured" in error_msg2:
            print("Warning: Skipping OpenAPI generation - configuration not available")
            print("OpenAPI spec will be generated at runtime")
            sys.exit(0)
        print(f"Error: Cannot import app: {e2}")
        print("OpenAPI generation skipped - will be generated at runtime")
        sys.exit(0)

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