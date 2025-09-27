"""
Object Storage Service

This module handles all media object-related storage operations including
CRUD operations and object management.
"""

import logging
from typing import Optional, List
from datetime import datetime, timezone

from fastapi import HTTPException
from .interfaces import StorageInterface
from ..models import Object

logger = logging.getLogger(__name__)


class ObjectStorageService:
    """Handles media object-related storage operations"""
    
    def __init__(self, vast_db, s3_client):
        self.vast_db = vast_db
        self.s3_client = s3_client
    
    async def get_object(self, object_id: str) -> Optional[Object]:
        """Get a specific object by ID"""
        try:
            result = self.vast_db.query("objects").select("*").where(f"id = '{object_id}'").execute()
            
            if not result or len(result) == 0:
                return None
            
            object_data = dict(result[0])
            return Object(**object_data)
        except Exception as e:
            logger.error("Failed to get object %s: %s", object_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def create_object(self, obj: Object) -> bool:
        """Create a new object"""
        try:
            now = datetime.now(timezone.utc)
            obj.created = now
            
            object_data = obj.model_dump()
            self.vast_db.insert_record("objects", object_data)
            return True
        except Exception as e:
            logger.error("Failed to create object: %s", e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def delete_object(self, object_id: str) -> bool:
        """Delete an object"""
        try:
            self.vast_db.query("objects").delete().where(f"id = '{object_id}'").execute()
            return True
        except Exception as e:
            logger.error("Failed to delete object %s: %s", object_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def get_objects(self) -> List[Object]:
        """Get all objects"""
        try:
            result = self.vast_db.query("objects").select("*").execute()
            
            objects = []
            for row in result:
                object_data = dict(row)
                objects.append(Object(**object_data))
            
            return objects
        except Exception as e:
            logger.error("Failed to get objects: %s", e)
            raise HTTPException(status_code=500, detail="Internal server error")
