"""
Objects submodule for TAMS API.
Handles object-related operations and business logic.
"""
from typing import List, Optional, Dict
from fastapi import HTTPException
from datetime import datetime, timezone
from ..models.models import Object
from ..storage.vast_store import VASTStore
import logging

logger = logging.getLogger(__name__)

# Standalone functions for router use
async def get_object(store: VASTStore, object_id: str) -> Optional[Object]:
    """Get a specific object by ID"""
    try:
        obj = await store.get_object(object_id)
        return obj
    except Exception as e:
        logger.error(f"Failed to get object {object_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

async def create_object(store: VASTStore, obj: Object) -> bool:
    """Create a new object"""
    try:
        now = datetime.now(timezone.utc)
        obj.created = now
        success = await store.create_object(obj)
        return success
    except Exception as e:
        logger.error(f"Failed to create object: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

async def delete_object(store: VASTStore, object_id: str) -> bool:
    """Delete an object (hard delete only - TAMS compliant)"""
    try:
        success = await store.delete_object(object_id)
        return success
    except Exception as e:
        logger.error(f"Failed to delete object {object_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

class ObjectManager:
    """Manager for object operations (create, retrieve, update, delete, etc.)."""
    def __init__(self, store: Optional[VASTStore] = None):
        self.store = store

    async def get_object(self, object_id: str, store: Optional[VASTStore] = None) -> Object:
        store = store or self.store
        if store is None:
            raise HTTPException(status_code=500, detail="VAST store is not initialized")
        try:
            obj = await store.get_object(object_id)
            if not obj:
                raise HTTPException(status_code=404, detail="Object not found")
            return obj
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get object {object_id}: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

    async def create_object(self, obj: Object, store: Optional[VASTStore] = None) -> Object:
        store = store or self.store
        if store is None:
            raise HTTPException(status_code=500, detail="VAST store is not initialized")
        try:
            now = datetime.now(timezone.utc)
            obj.created = now
            success = await store.create_object(obj)
            if not success:
                raise HTTPException(status_code=500, detail="Failed to create object")
            return obj
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to create object: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

    async def delete_object(self, object_id: str, store: Optional[VASTStore] = None):
        store = store or self.store
        if store is None:
            raise HTTPException(status_code=500, detail="VAST store is not initialized")
        try:
            success = await store.delete_object(object_id)
            if not success:
                raise HTTPException(status_code=404, detail="Object not found")
            
            return {"message": "Object hard deleted"}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to delete object {object_id}: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

 