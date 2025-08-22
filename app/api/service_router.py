"""
Service API router for TAMS
"""
from fastapi import APIRouter, Depends, HTTPException
from ..core.dependencies import get_vast_store
from ..storage.vast_store import VASTStore
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/service", tags=["service"])

@router.head("/storage-backends")
async def head_storage_backends():
    """Return storage backends path headers"""
    return {}

@router.get("/storage-backends")
async def get_storage_backends(
    store: VASTStore = Depends(get_vast_store)
):
    """Provide information about the storage backends available on this service instance"""
    try:
        storage_backends = await store.get_storage_backends()
        return storage_backends
    except Exception as e:
        logger.error("Failed to get storage backends: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")
