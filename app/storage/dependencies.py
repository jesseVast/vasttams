"""
Storage Dependencies

This module provides dependency injection functions for the storage service,
abstracting away the concrete storage implementations from the API layer.
"""

from functools import lru_cache
from ..core.dependencies import get_vast_db, get_s3_client
from .main_service import TAMSStorageService
from .interfaces import StorageInterface

# Global storage service instance
_storage_service: StorageInterface = None


@lru_cache()
def get_storage_service() -> StorageInterface:
    """
    Get the global TAMS storage service instance.
    
    This function provides a singleton instance of the storage service,
    ensuring consistent state across the application.
    
    Returns:
        StorageInterface: The configured storage service instance
    """
    global _storage_service
    if _storage_service is None:
        _storage_service = TAMSStorageService(
            vast_db=get_vast_db(),
            s3_client=get_s3_client()
        )
    return _storage_service


def reset_storage_service():
    """
    Reset the storage service instance.
    
    This is primarily used for testing to ensure clean state
    between test cases.
    """
    global _storage_service
    _storage_service = None
    get_storage_service.cache_clear()
