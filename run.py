#!/usr/bin/env python3
"""
TAMS FastAPI Application Runner

This script starts the TAMS (Time-addressable Media Store) API server.
"""

import uvicorn
import logging
from vasttams.core.config import get_settings

def main():
    """Start the VastTAMS API server"""
    settings = get_settings()
    
    # Configure logging based on environment
    log_level = getattr(logging, settings.log_level.upper())
    log_format = settings.log_format
    logging.basicConfig(level=log_level, format=log_format)
    
    logger = logging.getLogger(__name__)
    logger.info(f"Starting VastTAMS API server on {settings.host}:{settings.port}")
    
    # Start the server (note: need to update path to src/vasttams)
    uvicorn.run(
        "vasttams.main:app",
        host=settings.host,
        port=settings.port,
        reload=False,  # Disable auto-reload for production-like testing
        log_level=settings.log_level.lower()
    )

if __name__ == "__main__":
    main()