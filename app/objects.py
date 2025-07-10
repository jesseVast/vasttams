"""
Objects submodule for TAMS API.
Handles object-related operations and business logic.
"""
from typing import Optional
from fastapi import HTTPException
from datetime import datetime, timezone
from .models import Object
from .vast_store import VASTStore
import logging

logger = logging.getLogger(__name__)

class ObjectManager:
    """Manager for object operations (create, retrieve, update, delete, etc.)."""
    def __init__(self, store: Optional[VASTStore] = None):
        self.store = store

    async def get_object(self, object_id: str, store: Optional[VASTStore] = None) -> Object:
        """
        Retrieve an object by its unique identifier.

        Args:
            object_id (str): The unique identifier of the object to retrieve.
            store (Optional[VASTStore]): Optional VASTStore instance to use. Defaults to the manager's store.

        Returns:
            Object: The object corresponding to the given ID.

        Raises:
            HTTPException: 404 if the object is not found, 500 for internal errors or if the store is not initialized.
        """
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
        """
        Create a new object and store it in the database.

        Args:
            obj (Object): The object to create.
            store (Optional[VASTStore]): Optional VASTStore instance to use. Defaults to the manager's store.

        Returns:
            Object: The created object.

        Raises:
            HTTPException: 500 if the VAST store is not initialized or creation fails.
        """
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

    async def delete_object(self, object_id: str, store: VASTStore) -> bool:
        return await store.delete_object(object_id) 