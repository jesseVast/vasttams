"""
TAMS Storage Backends Module

This module handles storage backend management including:
- CRUD operations for storage backends
- Validation of backend usage before deletion
- Support for multiple storage backends per TAMS instance
"""

from .models import StorageBackend, StorageBackendsList
from .service import StorageBackendService
from .router import router

__all__ = [
    "StorageBackend",
    "StorageBackendsList", 
    "StorageBackendService",
    "router"
]

