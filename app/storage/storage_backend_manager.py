"""
Storage Backend Manager for TAMS get_urls generation

This module manages storage backend information and provides metadata
for generating TAMS-compliant get_urls objects.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import uuid

logger = logging.getLogger(__name__)


class StorageBackendManager:
    """Manages storage backend information for get_urls generation"""
    
    def __init__(self):
        self.storage_backends = {}
        self._initialize_default_storage_backends()
    
    def _initialize_default_storage_backends(self):
        """Initialize with default storage backend information"""
        # Default storage backend for S3-compatible storage
        self.storage_backends["default"] = {
            "id": "default",
            "store_type": "http_object_store",
            "provider": "S3-Compatible",
            "region": "default",
            "availability_zone": None,
            "store_product": "S3-Compatible Storage",
            "label": "Default S3-Compatible Storage",
            "description": "Default storage backend for TAMS media objects"
        }
        
        # Add more storage backends as needed
        # This could be loaded from configuration or database in the future
    
    def get_storage_backend_info(self, storage_id: str) -> Dict[str, Any]:
        """Get storage backend metadata by ID"""
        return self.storage_backends.get(storage_id, self.storage_backends["default"])
    
    def list_storage_backends(self) -> List[Dict[str, Any]]:
        """List all available storage backends"""
        return list(self.storage_backends.values())
    
    def add_storage_backend(self, backend_info: Dict[str, Any]) -> bool:
        """Add a new storage backend"""
        try:
            backend_id = backend_info.get("id")
            if not backend_id:
                backend_id = str(uuid.uuid4())
                backend_info["id"] = backend_id
            
            self.storage_backends[backend_id] = backend_info
            logger.info(f"Added storage backend: {backend_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to add storage backend: {e}")
            return False
    
    def remove_storage_backend(self, storage_id: str) -> bool:
        """Remove a storage backend (except default)"""
        if storage_id == "default":
            logger.warning("Cannot remove default storage backend")
            return False
        
        try:
            if storage_id in self.storage_backends:
                del self.storage_backends[storage_id]
                logger.info(f"Removed storage backend: {storage_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to remove storage backend {storage_id}: {e}")
            return False
    
    def update_storage_backend(self, storage_id: str, updates: Dict[str, Any]) -> bool:
        """Update storage backend information"""
        try:
            if storage_id in self.storage_backends:
                self.storage_backends[storage_id].update(updates)
                logger.info(f"Updated storage backend: {storage_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to update storage backend {storage_id}: {e}")
            return False
