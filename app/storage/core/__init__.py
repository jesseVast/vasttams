"""
Core storage infrastructure modules

This module provides pure storage operations without any TAMS-specific logic.

TAMS ARCHITECTURE:
==================

CORE COMPONENTS:
- S3Core: Pure S3 operations (no TAMS logic)
- VASTCore: Pure VAST operations (no TAMS logic)
- StorageFactory: Component creation and management

SEPARATION OF CONCERNS:
- Core modules: Pure infrastructure operations
- Endpoint modules: TAMS-specific business logic
- Clear boundaries between infrastructure and application

This architecture ensures TAMS compliance while maintaining
clean separation between core storage and business logic.
"""

from .s3_core import S3Core
from .vast_core import VASTCore

__all__ = [
    "S3Core",
    "VASTCore"
]
