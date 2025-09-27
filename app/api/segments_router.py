"""
Minimal Segments Router

This is a minimal working segments router that uses the new storage service architecture.
It provides basic endpoint structure that can be expanded later.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from typing import List, Optional
from pydantic import ValidationError
from ..models import FlowSegment, FlowStorage, FlowStoragePost
from ..storage import get_storage_service
from ..storage.interfaces import StorageInterface
from ..core.event_manager import EventManager
from ..core.utils import log_pydantic_validation_error, safe_model_parse
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/flows", tags=["segments"])

# HEAD endpoint
@router.head("/{flow_id}/segments")
async def head_flow_segments(flow_id: str):
    """Return flow segments path headers"""
    return {}

# GET endpoint
@router.get("/{flow_id}/segments", response_model=List[FlowSegment])
async def list_flow_segments(
    flow_id: str,
    timerange: Optional[str] = Query(None, description="Filter by time range"),
    storage: StorageInterface = Depends(get_storage_service)
):
    """List segments for a specific flow"""
    try:
        segments = await storage.get_flow_segments(flow_id, timerange)
        return segments
    except Exception as e:
        logger.error("Failed to list segments for flow %s: %s", flow_id, e)
        raise HTTPException(status_code=500, detail="Internal server error")

# POST endpoint for creating flow segments
@router.post("/{flow_id}/segments", response_model=FlowSegment, status_code=201)
async def create_new_flow_segment(
    flow_id: str,
    segment: FlowSegment = Body(...),
    storage: StorageInterface = Depends(get_storage_service)
):
    """Create a new flow segment"""
    try:
        # Validate segment data
        if not segment.object_id:
            raise HTTPException(status_code=400, detail="object_id is required")
        if not segment.timerange:
            raise HTTPException(status_code=400, detail="timerange is required")
        
        # Create segment using storage service
        success = await storage.create_flow_segment(flow_id, segment)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to create segment")
        
        # Emit segment created event
        try:
            event_manager = EventManager(storage)
            await event_manager.emit_flow_segment_event('flow-segments/created', segment)
        except Exception as e:
            logger.warning("Failed to emit segment created event: %s", e)
        
        return segment
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to create segment for flow %s: %s", flow_id, e)
        raise HTTPException(status_code=500, detail="Internal server error")

# DELETE endpoint
@router.delete("/{flow_id}/segments")
async def delete_flow_segments_by_id(
    flow_id: str,
    timerange: Optional[str] = Query(None, description="Filter by time range"),
    storage: StorageInterface = Depends(get_storage_service)
):
    """Delete segments for a specific flow"""
    try:
        success = await storage.delete_flow_segments(flow_id, timerange)
        if not success:
            raise HTTPException(status_code=404, detail="No segments found to delete")
        
        return {"message": "Segments deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete segments for flow %s: %s", flow_id, e)
        raise HTTPException(status_code=500, detail="Internal server error")

# Storage allocation endpoint
@router.post("/{flow_id}/storage", response_model=FlowStorage, status_code=201)
async def create_flow_storage_by_id(
    flow_id: str,
    request: FlowStoragePost,
    storage: StorageInterface = Depends(get_storage_service)
):
    """Allocate storage locations for writing media objects"""
    try:
        # Use storage service to allocate storage
        flow_storage = await storage.allocate_flow_storage(flow_id, request)
        return flow_storage
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to allocate storage for flow %s: %s", flow_id, e)
        raise HTTPException(status_code=500, detail="Internal server error")
