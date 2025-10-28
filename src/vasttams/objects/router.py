from fastapi import APIRouter, Depends, HTTPException, Query, Body
from typing import List, Optional
from pydantic import ValidationError
from .models import Object, ObjectInstance, ObjectInstancePost
from ..common.storage import get_storage_service
from ..common.storage.interfaces import StorageInterface
from ..events import EventManager
from ..core.dependencies import get_vast_db
from ..core.utils import log_pydantic_validation_error, safe_model_parse
from ..auth.rbac import require_admin, require_editor, require_viewer
from ..auth.middleware import UserSession
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/objects", tags=["objects"])

# HEAD endpoint
@router.head("/{object_id}")
async def head_object(object_id: str):
    """Return object path headers"""
    return {}

@router.options("")
async def options_objects():
    """Objects endpoint OPTIONS method for CORS preflight"""
    return {}

# GET endpoint - List all objects
@router.get("", response_model=List[Object])
async def list_objects(
    storage: StorageInterface = Depends(get_storage_service)
):
    """List all objects"""
    try:
        objects = await storage.get_objects()
        return objects
    except Exception as e:
        logger.error("Failed to list objects: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")

# GET endpoint - Get specific object by ID
@router.get("/{object_id}", response_model=Object)
async def get_object_by_id(
    object_id: str,
    storage: StorageInterface = Depends(get_storage_service),
    user_session: UserSession = Depends(require_viewer)
):
    """Get a specific object by ID"""
    try:
        obj = await storage.get_object(object_id)
        if not obj:
            raise HTTPException(status_code=404, detail="Object not found")
        return obj
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get object %s: %s", object_id, e)
        raise HTTPException(status_code=500, detail="Internal server error")

# Note: POST /objects endpoint removed - TAMS API uses POST /flows/{flowId}/storage for object allocation

# Note: Batch POST /objects endpoint removed - TAMS API uses POST /flows/{flowId}/storage for object allocation

# DELETE endpoint
@router.delete("/{object_id}")
async def delete_object_by_id(
    object_id: str,
    storage: StorageInterface = Depends(get_storage_service),
    user_session: UserSession = Depends(require_admin)
):
    """Delete an object (hard delete only - TAMS compliant)"""
    try:
        # Get object before deletion for event emission
        obj = await storage.get_object(object_id)
        
        success = await storage.delete_object(object_id)
        if not success:
            raise HTTPException(status_code=404, detail="Object not found")
        
        # Emit object deleted event
        if obj:
            try:
                vast_db = get_vast_db()
                event_manager = EventManager(vast_db)
                await event_manager.emit_object_event('objects/deleted', obj)
            except Exception as e:
                logger.warning("Failed to emit object deleted event: %s", e)
        
        return {"message": "Object hard deleted successfully"}
        
    except ValueError as e:
        # Handle dependency violations with 409 Conflict
        logger.warning("Dependency violation deleting object %s: %s", object_id, e)
        raise HTTPException(status_code=409, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete object %s: %s", object_id, e)
        raise HTTPException(status_code=500, detail="Internal server error")


# Object Instances Management (TAMS 8.0)

@router.post("/{object_id}/instances", response_model=ObjectInstance)
async def create_object_instance(
    object_id: str,
    instance: ObjectInstancePost = Body(...),
    storage: StorageInterface = Depends(get_storage_service)
):
    """Register a new instance for an object (TAMS 8.0)"""
    try:
        # Validate that object exists
        obj = await storage.get_object(object_id)
        if not obj:
            raise HTTPException(status_code=404, detail="Object not found")
        
        # Create instance via storage service
        instance_obj = ObjectInstance(
            label=instance.label,
            storage_id=instance.storage_id,
            url=instance.url,
            controlled=instance.controlled,
            metadata=instance.metadata
        )
        
        success = await storage.create_object_instance(object_id, instance_obj)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to create object instance")
        
        return instance_obj
        
    except HTTPException:
        raise
    except ValidationError as e:
        log_pydantic_validation_error("Object Instance", e)
        raise HTTPException(status_code=400, detail="Invalid object instance data")
    except Exception as e:
        logger.error("Failed to create object instance for %s: %s", object_id, e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{object_id}/instances", response_model=List[ObjectInstance])
async def list_object_instances(
    object_id: str,
    storage: StorageInterface = Depends(get_storage_service),
    user_session: UserSession = Depends(require_viewer)
):
    """List all instances for an object (TAMS 8.0)"""
    try:
        # Validate that object exists
        obj = await storage.get_object(object_id)
        if not obj:
            raise HTTPException(status_code=404, detail="Object not found")
        
        # Get instances via storage service
        instances = await storage.list_object_instances(object_id)
        return instances
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to list object instances for %s: %s", object_id, e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{object_id}/instances")
async def delete_object_instance(
    object_id: str,
    label: Optional[str] = Query(None, description="Delete instance with this label"),
    storage_id: Optional[str] = Query(None, description="Delete instance with this storage_id"),
    storage: StorageInterface = Depends(get_storage_service)
):
    """Delete an object instance by label or storage_id (TAMS 8.0)"""
    try:
        # Validate that object exists
        obj = await storage.get_object(object_id)
        if not obj:
            raise HTTPException(status_code=404, detail="Object not found")
        
        # Either label or storage_id must be provided
        if not label and not storage_id:
            raise HTTPException(status_code=400, detail="Either label or storage_id must be provided")
        
        # Delete instance via storage service
        success = await storage.delete_object_instance(object_id, label=label, storage_id=storage_id)
        if not success:
            raise HTTPException(status_code=404, detail="Object instance not found")
        
        return {"message": "Object instance deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete object instance for %s: %s", object_id, e)
        raise HTTPException(status_code=500, detail="Internal server error")

 