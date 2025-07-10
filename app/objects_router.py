from fastapi import APIRouter, Depends, HTTPException
from .models import Object
from .vast_store import VASTStore
from .dependencies import get_vast_store
from .objects import ObjectManager
import logging

router = APIRouter()
logger = logging.getLogger(__name__)
object_manager = ObjectManager()

@router.head("/objects/{object_id}")
async def head_object(object_id: str):
    return {}

@router.get("/objects/{object_id}", response_model=Object)
async def get_object(object_id: str, store: VASTStore = Depends(get_vast_store)):
    return await object_manager.get_object(object_id, store)

@router.post("/objects", response_model=Object, status_code=201)
async def create_object(obj: Object, store: VASTStore = Depends(get_vast_store)):
    return await object_manager.create_object(obj, store)

@router.delete("/objects/{object_id}")
async def delete_object(object_id: str, store: VASTStore = Depends(get_vast_store)):
    """Delete an object by its unique identifier."""
    try:
        success = await object_manager.delete_object(object_id, store)
        if not success:
            raise HTTPException(status_code=404, detail="Object not found")
        return {"message": "Object deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete object {object_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error") 