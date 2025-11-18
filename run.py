#!/usr/bin/env python3
"""
TAMS FastAPI Application Runner

This script starts the TAMS (Time-addressable Media Store) API server.
"""

import sys
import os
from pathlib import Path

# Add src/server to Python path to allow importing vasttamsserver
project_root = Path(__file__).parent
server_path = project_root / "src" / "server"
if str(server_path) not in sys.path:
    sys.path.insert(0, str(server_path))

import uvicorn
import logging
from vasttamsserver.core.config import get_settings

def main():
    """Start the VastTAMS API server"""
    settings = get_settings()
    
    # Configure logging based on environment
    log_level = getattr(logging, settings.log_level.upper())
    log_format = settings.log_format
    logging.basicConfig(level=log_level, format=log_format)
    
    logger = logging.getLogger(__name__)
    logger.info(f"Starting VastTAMS API server on {settings.host}:{settings.port}")
    
    # Start the server
    # Use multiple workers for better concurrency handling
    # Workers can be configured via:
    # 1. Settings.workers (from config.yaml or TAMS_WORKERS env var)
    # 2. UVICORN_WORKERS environment variable (takes precedence)
    import os
    workers = int(os.getenv("UVICORN_WORKERS", str(settings.workers)))
    
    logger.info(f"Starting server with {workers} worker(s) on {settings.host}:{settings.port}")
    
    uvicorn.run(
        "vasttamsserver.main:app",
        host=settings.host,
        port=settings.port,
        workers=workers,  # Multiple workers for better concurrency
        reload=False,  # Disable auto-reload for production-like testing
        log_level=settings.log_level.lower(),
        loop="asyncio",  # Use asyncio event loop
        access_log=True  # Enable access logging for monitoring
    )

if __name__ == "__main__":
    main()