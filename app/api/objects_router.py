from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from pydantic import ValidationError
from ..models import Object
from ..storage import get_storage_service
from ..storage.interfaces import StorageInterface
from ..core.event_manager import EventManager
from ..core.utils import log_pydantic_validation_error, safe_model_parse
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/objects", tags=["objects"])

# HEAD endpoint
@router.head("/{object_id}")
async def head_object(object_id: str):
    """Return object path headers"""
    return {}

@router.options("/objects")
async def options_objects():
    """Objects endpoint OPTIONS method for CORS preflight"""
    return {}

# GET endpoint
@router.get("/{object_id}", response_model=Object)
async def get_object_by_id(
    object_id: str,
    storage: StorageInterface = Depends(get_storage_service)
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
    storage: StorageInterface = Depends(get_storage_service)
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
                event_manager = EventManager(storage)
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

 