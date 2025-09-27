"""
Deletion Requests API router for TAMS
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import List
from ..models import DeletionRequest, DeletionRequestsList
from ..storage import get_storage_service
from ..storage.interfaces import StorageInterface
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/flow-delete-requests", tags=["deletion-requests"])

@router.get("")
async def get_deletion_requests(
    storage: StorageInterface = Depends(get_storage_service)
):
    """Get the list of deletion requests"""
    try:
        deletion_requests = await storage.get_deletion_requests()
        return deletion_requests
    except Exception as e:
        logger.error("Failed to get deletion requests: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("")
async def create_deletion_request(
    deletion_request: DeletionRequest,
    storage: StorageInterface = Depends(get_storage_service)
):
    """Create a new deletion request"""
    try:
        created_request = await storage.create_deletion_request(deletion_request)
        return created_request
    except Exception as e:
        logger.error("Failed to create deletion request: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{request_id}")
async def get_deletion_request(
    request_id: str,
    storage: StorageInterface = Depends(get_storage_service)
):
    """Get a specific deletion request by ID"""
    try:
        deletion_request = await storage.get_deletion_request(request_id)
        if not deletion_request:
            raise HTTPException(status_code=404, detail="Deletion request not found")
        return deletion_request
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get deletion request: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/{request_id}")
async def delete_deletion_request(
    request_id: str,
    storage: StorageInterface = Depends(get_storage_service)
):
    """Delete a deletion request"""
    try:
        success = await storage.delete_deletion_request(request_id)
        if not success:
            raise HTTPException(status_code=404, detail="Deletion request not found")
        return {"message": "Deletion request deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete deletion request: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")

