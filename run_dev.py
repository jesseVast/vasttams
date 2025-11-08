#!/usr/bin/env python3
"""
TAMS FastAPI Development Server Runner

This script starts the TAMS API server in development mode with auto-reload enabled.
Use this for local development to automatically restart the server when code changes.
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
    """Start the VastTAMS API server in development mode"""
    settings = get_settings()
    
    # Configure logging for development
    log_level = getattr(logging, settings.log_level.upper())
    log_format = settings.log_format
    logging.basicConfig(level=log_level, format=log_format)
    
    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("Starting VastTAMS API server in DEVELOPMENT MODE")
    logger.info("=" * 60)
    logger.info(f"Server: {settings.host}:{settings.port}")
    logger.info(f"Auto-reload: ENABLED")
    logger.info(f"Log level: {settings.log_level}")
    logger.info(f"API docs: http://{settings.host}:{settings.port}/docs")
    logger.info("=" * 60)
    
    # Development mode: single worker with auto-reload
    # Note: reload=True requires a single worker
    uvicorn.run(
        "vasttamsserver.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,  # Enable auto-reload for development
        reload_dirs=["src/server/vasttamsserver"],  # Watch these directories for changes
        reload_includes=["*.py"],  # Watch Python files
        log_level=settings.log_level.lower(),
        loop="asyncio",
        access_log=True,
        # Additional development options
        reload_excludes=["*.pyc", "__pycache__", "*.pyo", "*.pyd", ".git"],
        use_colors=True  # Colored terminal output
    )

if __name__ == "__main__":
    main()

