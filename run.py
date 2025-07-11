#!/usr/bin/env python3
"""
TAMS FastAPI Application Runner

This script starts the TAMS (Time-addressable Media Store) API server.
"""

import uvicorn
import logging
from app.config import get_settings

def main():
    """Start the TAMS API server"""
    settings = get_settings()
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper()),
        format=settings.log_format
    )
    
    logger = logging.getLogger(__name__)
    logger.info(f"Starting TAMS API server on {settings.host}:{settings.port}")
    
    # Start the server
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )

if __name__ == "__main__":
    main()