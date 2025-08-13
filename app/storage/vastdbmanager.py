"""
VastDBManager - VAST Database Manager

This module provides a high-level interface for managing VAST databases,
including table operations, query optimization, and analytics.

The module has been refactored into a modular architecture for better
maintainability and extensibility.
"""

# Import the refactored VastDBManager from the modular structure
from .vastdbmanager.core import VastDBManager

# Backward compatibility - export the main class
__all__ = ['VastDBManager']

# Version information
__version__ = "2.0.0"