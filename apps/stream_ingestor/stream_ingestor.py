#!/usr/bin/env python3
"""
Stream Ingestor Application - Main Entry Point

This is a thin wrapper that calls the CLI module.
For backward compatibility, this file can still be used directly.
"""

import sys
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Import and run the CLI
from stream_ingestor.cli import main
import asyncio

if __name__ == "__main__":
    asyncio.run(main())

