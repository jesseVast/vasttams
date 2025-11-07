"""
Deletion Requests API router for TAMS
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import List
from ..models import DeletionRequest, DeletionRequestsList
from ..common.storage.dependencies import get_storage_service
from ..common.storage.interfaces import StorageInterface
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



