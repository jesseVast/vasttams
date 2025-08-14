from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from ..models.models import Object
from .objects import get_object, create_object, delete_object
from ..storage.vast_store import VASTStore
from ..core.dependencies import get_vast_store
import logging

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
        logger.error(f"Failed to get object {object_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# POST endpoint
@router.post("/objects", response_model=Object, status_code=201)
async def create_new_object(
    obj: Object,
    store: VASTStore = Depends(get_vast_store)
):
    """Create a new object"""
    try:
        success = await create_object(store, obj)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to create object")
        return obj
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create object: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Batch POST endpoint
@router.post("/objects/batch", response_model=List[Object], status_code=201)
async def create_objects_batch(
    objects: List[Object],
    store: VASTStore = Depends(get_vast_store)
):
    """Create multiple objects in a single batch operation"""
    try:
        created_objects = []
        for obj in objects:
            success = await create_object(store, obj)
            if success:
                created_objects.append(obj)
            else:
                logger.warning(f"Failed to create object {obj.object_id}")
        
        if not created_objects:
            raise HTTPException(status_code=500, detail="Failed to create any objects")
        
        logger.info(f"Successfully created {len(created_objects)}/{len(objects)} objects in batch")
        return created_objects
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create objects batch: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# DELETE endpoint
@router.delete("/objects/{object_id}")
async def delete_object_by_id(
    object_id: str,
    soft_delete: bool = Query(True, description="Use soft delete"),
    deleted_by: str = Query("system", description="User performing the deletion"),
    store: VASTStore = Depends(get_vast_store)
):
    """Delete an object"""
    try:
        success = await delete_object(store, object_id, soft_delete, deleted_by)
        if not success:
            raise HTTPException(status_code=404, detail="Object not found")
        return {"message": "Object deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete object {object_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

 