"""
VastTAMS (Time-addressable Media Store) API

A comprehensive FastAPI implementation with VAST database integration
for storing and managing time-addressable media flows.

Version 8.0
"""

__version__ = "8.0.0"
__author__ = "Jesse Thaloor"
__description__ = "Time-addressable Media Store API"

# Don't import app by default to avoid loading FastAPI unnecessarily
# Import directly: from vasttams.main import app
__all__ = ["__version__"]

