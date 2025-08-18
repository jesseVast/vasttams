#!/usr/bin/env python3
"""
TAMS FastAPI Application Runner

This script starts the TAMS (Time-addressable Media Store) API server.
"""

import uvicorn
import logging
from app.core.config import get_settings

def main():
    """Start the TAMS API server"""
    settings = get_settings()
    
    # Configure logging based on environment
    log_level = getattr(logging, settings.log_level.upper())
    log_format = settings.log_format
    logging.basicConfig(level=log_level, format=log_format)
    
    logger = logging.getLogger(__name__)
    logger.info(f"Starting TAMS API server on {settings.host}:{settings.port}")
    
    # Start the server
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=False,  # Disable auto-reload for production-like testing
        log_level=settings.log_level.lower()
    )

if __name__ == "__main__":
    main()