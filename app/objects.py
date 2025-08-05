"""
Objects module for TAMS API

This module provides functions for managing media objects in the TAMS system.
"""

import logging
from typing import Optional, List, Dict, Any
from uuid import UUID
from app.models import Object
from app.vast_store import VASTStore

logger = logging.getLogger(__name__)

async def get_object(store: VASTStore, object_id: str) -> Optional[Object]:
    """
    Get a media object by ID
    
    Args:
        store: VAST store instance
        object_id: Object identifier
        
    Returns:
        Object instance or None if not found
    """
    try:
        # Get object from store
        obj_data = await store.get_object(object_id)
        if not obj_data:
            return None
            
        # Convert to new schema format
        # Assuming obj_data contains flow_references in old format
        flow_references = obj_data.get('flow_references', [])
        referenced_by_flows = []
        first_referenced_by_flow = None
        
        for ref in flow_references:
            if isinstance(ref, dict) and 'flow_id' in ref:
                flow_id = ref['flow_id']
                try:
                    uuid_obj = UUID(flow_id)
                    referenced_by_flows.append(uuid_obj)
                    if first_referenced_by_flow is None:
                        first_referenced_by_flow = uuid_obj
                except ValueError:
                    logger.warning(f"Invalid UUID format for flow_id: {flow_id}")
            elif isinstance(ref, str):
                try:
                    uuid_obj = UUID(ref)
                    referenced_by_flows.append(uuid_obj)
                    if first_referenced_by_flow is None:
                        first_referenced_by_flow = uuid_obj
                except ValueError:
                    logger.warning(f"Invalid UUID format for flow_id: {ref}")
        
        return Object(
            id=object_id,  # Use id instead of object_id
            referenced_by_flows=referenced_by_flows,
            first_referenced_by_flow=first_referenced_by_flow
        )
        
    except Exception as e:
        logger.error(f"Error getting object {object_id}: {e}")
        raise

async def create_object(store: VASTStore, obj: Object) -> bool:
    """
    Create a new media object
    
    Args:
        store: VAST store instance
        obj: Object to create
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Convert new schema to old format for store
        flow_references = []
        for flow_id in obj.referenced_by_flows:
            flow_references.append({'flow_id': str(flow_id)})
            
        obj_data = {
            'object_id': obj.id,  # Convert id back to object_id for store
            'flow_references': flow_references
        }
        
        success = await store.create_object(obj_data)
        return success
        
    except Exception as e:
        logger.error(f"Error creating object {obj.id}: {e}")
        return False

async def delete_object(store: VASTStore, object_id: str, soft_delete: bool = True, deleted_by: str = "system") -> bool:
    """
    Delete a media object
    
    Args:
        store: VAST store instance
        object_id: Object identifier
        soft_delete: Whether to use soft delete
        deleted_by: User performing the deletion
        
    Returns:
        True if successful, False otherwise
    """
    try:
        success = await store.delete_object(object_id, soft_delete=soft_delete, deleted_by=deleted_by)
        return success
        
    except Exception as e:
        logger.error(f"Error deleting object {object_id}: {e}")
        return False

async def list_objects(store: VASTStore, page: Optional[str] = None, limit: Optional[int] = None) -> List[Object]:
    """
    List media objects with pagination
    
    Args:
        store: VAST store instance
        page: Pagination key
        limit: Number of items per page
        
    Returns:
        List of Object instances
    """
    try:
        objects_data = await store.list_objects(page=page, limit=limit)
        objects = []
        
        for obj_data in objects_data:
            # Convert each object to new schema format
            flow_references = obj_data.get('flow_references', [])
            referenced_by_flows = []
            first_referenced_by_flow = None
            
            for ref in flow_references:
                if isinstance(ref, dict) and 'flow_id' in ref:
                    flow_id = ref['flow_id']
                    try:
                        uuid_obj = UUID(flow_id)
                        referenced_by_flows.append(uuid_obj)
                        if first_referenced_by_flow is None:
                            first_referenced_by_flow = uuid_obj
                    except ValueError:
                        logger.warning(f"Invalid UUID format for flow_id: {flow_id}")
                elif isinstance(ref, str):
                    try:
                        uuid_obj = UUID(ref)
                        referenced_by_flows.append(uuid_obj)
                        if first_referenced_by_flow is None:
                            first_referenced_by_flow = uuid_obj
                    except ValueError:
                        logger.warning(f"Invalid UUID format for flow_id: {ref}")
            
            obj = Object(
                id=obj_data.get('object_id', obj_data.get('id', '')),
                referenced_by_flows=referenced_by_flows,
                first_referenced_by_flow=first_referenced_by_flow
            )
            objects.append(obj)
            
        return objects
        
    except Exception as e:
        logger.error(f"Error listing objects: {e}")
        return []

class ObjectManager:
    """Manager for object operations (create, retrieve, update, delete, etc.)."""
    def __init__(self, store: Optional[VASTStore] = None):
        self.store = store

    async def get_object(self, object_id: str, store: Optional[VASTStore] = None) -> Object:
        store = store or self.store
        if store is None:
            raise Exception("VAST store is not initialized")
        try:
            obj = await get_object(store, object_id)
            if not obj:
                raise Exception("Object not found")
            return obj
        except Exception as e:
            logger.error(f"Failed to get object {object_id}: {e}")
            raise

    async def create_object(self, obj: Object, store: Optional[VASTStore] = None) -> Object:
        store = store or self.store
        if store is None:
            raise Exception("VAST store is not initialized")
        try:
            success = await create_object(store, obj)
            if not success:
                raise Exception("Failed to create object")
            return obj
        except Exception as e:
            logger.error(f"Failed to create object: {e}")
            raise

    async def delete_object(self, object_id: str, store: Optional[VASTStore] = None, soft_delete: bool = True, deleted_by: str = "system"):
        store = store or self.store
        if store is None:
            raise Exception("VAST store is not initialized")
        try:
            success = await delete_object(store, object_id, soft_delete=soft_delete, deleted_by=deleted_by)
            if not success:
                raise Exception("Object not found")
            
            delete_type = "soft deleted" if soft_delete else "hard deleted"
            return {"message": f"Object {delete_type}"}
        except Exception as e:
            logger.error(f"Failed to delete object {object_id}: {e}")
            raise

 