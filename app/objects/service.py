"""
Object Storage Service

This module handles all media object-related storage operations including
CRUD operations and object management.
"""

import logging
from typing import Optional, List
from datetime import datetime, timezone

from fastapi import HTTPException
from ..common.storage.interfaces import StorageInterface
from ..common.storage.timestamp_utils import get_tams_timestamp
from .models import Object, ObjectInstance

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
            
            # Handle VAST query result format
            rows = []
            if isinstance(result, dict) and 'data' in result:
                data = result['data']
                if isinstance(data, dict):
                    rows = list(data.values()) if data else []
                elif isinstance(data, list):
                    rows = data
            else:
                rows = result if isinstance(result, list) else []
            
            if not rows or len(rows) == 0:
                return None
            
            object_data = dict(rows[0]) if hasattr(rows[0], '__iter__') and not isinstance(rows[0], str) else rows[0]
            return Object(**object_data)
        except Exception as e:
            logger.error("Failed to get object %s: %s", object_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def create_object(self, obj: Object) -> bool:
        """Create a new object"""
        try:
            now = get_tams_timestamp()
            obj.created = now
            
            object_data = obj.model_dump()
            
            # Convert timestamp fields to PyArrow format using centralized function
            from app.storage.timestamp_utils import prepare_data_for_pyarrow
            object_data = prepare_data_for_pyarrow(object_data)
            
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
    
    # Object Instance Management (TAMS 8.0)
    
    async def create_object_instance(self, object_id: str, instance: ObjectInstance) -> bool:
        """Create a new instance for an object (TAMS 8.0)"""
        try:
            # Verify object exists
            obj = await self.get_object(object_id)
            if not obj:
                return False
            
            # Prepare instance data
            instance_data = instance.model_dump()
            instance_data['object_id'] = object_id
            instance_data['created'] = get_tams_timestamp()
            
            # Convert timestamp fields for PyArrow
            from app.storage.timestamp_utils import prepare_data_for_pyarrow
            instance_data = prepare_data_for_pyarrow(instance_data)
            
            # Insert instance record
            self.vast_db.insert_record("object_instances", instance_data)
            
            logger.info("Created object instance %s for object %s", instance.label, object_id)
            return True
        except Exception as e:
            logger.error("Failed to create object instance for %s: %s", object_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def list_object_instances(self, object_id: str) -> List[ObjectInstance]:
        """List all instances for an object (TAMS 8.0)"""
        try:
            # Verify object exists
            obj = await self.get_object(object_id)
            if not obj:
                return []
            
            # Query instances for this object
            result = self.vast_db.query("object_instances").select("*").where(f"object_id = '{object_id}'").execute()
            
            instances = []
            rows = result.get('data', []) if isinstance(result, dict) else result
            
            for row in rows:
                instance_data = dict(row)
                # Create ObjectInstance without object_id field (not part of model)
                instance_dict = {k: v for k, v in instance_data.items() if k in ['label', 'storage_id', 'url', 'controlled', 'metadata']}
                instances.append(ObjectInstance(**instance_dict))
            
            return instances
        except Exception as e:
            logger.error("Failed to list object instances for %s: %s", object_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def delete_object_instance(self, object_id: str, label: Optional[str] = None, storage_id: Optional[str] = None) -> bool:
        """Delete an object instance by label or storage_id (TAMS 8.0)"""
        try:
            # Verify object exists
            obj = await self.get_object(object_id)
            if not obj:
                return False
            
            # Build where clause
            if label:
                query = self.vast_db.query("object_instances").delete().where(f"object_id = '{object_id}' AND label = '{label}'")
            elif storage_id:
                query = self.vast_db.query("object_instances").delete().where(f"object_id = '{object_id}' AND storage_id = '{storage_id}'")
            else:
                return False
            
            query.execute()
            
            logger.info("Deleted object instance for object %s (label=%s, storage_id=%s)", object_id, label, storage_id)
            return True
        except Exception as e:
            logger.error("Failed to delete object instance for %s: %s", object_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")
