from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from pydantic import ValidationError
from ..models.models import Object
from .objects import get_object, create_object, delete_object
from ..storage.vast_store import VASTStore
from ..core.dependencies import get_vast_store
from ..core.event_manager import EventManager
from ..core.utils import log_pydantic_validation_error, safe_model_parse
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

router = APIRouter()

# HEAD endpoint
@router.head("/objects/{object_id}")
async def head_object(object_id: str):
    """Return object path headers"""
    return {}

@router.options("/objects")
async def options_objects():
    """Objects endpoint OPTIONS method for CORS preflight"""
    return {}

# GET endpoint
@router.get("/objects/{object_id}", response_model=Object)
async def get_object_by_id(
    object_id: str,
    store: VASTStore = Depends(get_vast_store)
):
    """Get a specific object by ID"""
    try:
        obj = await get_object(store, object_id)
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
@router.delete("/objects/{object_id}")
async def delete_object_by_id(
    object_id: str,
    store: VASTStore = Depends(get_vast_store)
):
    """Delete an object (hard delete only - TAMS compliant)"""
    try:
        # Get object before deletion for event emission
        obj = await get_object(store, object_id)
        
        success = await delete_object(store, object_id)
        if not success:
            raise HTTPException(status_code=404, detail="Object not found")
        
        # Emit object deleted event
        if obj:
            try:
                event_manager = EventManager(store)
                await event_manager.emit_object_event('objects/deleted', obj)
            except Exception as e:
                logger.warning("Failed to emit object deleted event: %s", e)
        
        return {"message": "Object hard deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete object %s: %s", object_id, e)
        raise HTTPException(status_code=500, detail="Internal server error")

 