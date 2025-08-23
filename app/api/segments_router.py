from fastapi import APIRouter, Depends, HTTPException, Query, Body
from typing import List, Optional
from pydantic import ValidationError
from ..models.models import FlowSegment, FlowStorage, FlowStoragePost
from .segments import get_flow_segments, create_flow_segment, delete_flow_segments, create_flow_storage, SegmentManager
from ..storage.vast_store import VASTStore
from ..storage.s3_store import S3Store
from ..core.dependencies import get_vast_store
from ..core.timerange_utils import get_storage_timerange
from ..core.event_manager import EventManager
from ..core.utils import log_pydantic_validation_error, safe_model_parse
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

async def check_flow_read_only(store: VASTStore, flow_id: str) -> None:
    """
    Check if a flow is read-only and raise 403 Forbidden if it is.
    
    Args:
        store: VAST store instance
        flow_id: Flow ID to check
        
    Raises:
        HTTPException: 403 Forbidden if flow is read-only
        HTTPException: 404 Not Found if flow doesn't exist
    """
    try:
        flow = await store.get_flow(flow_id)
        if not flow:
            raise HTTPException(status_code=404, detail="Flow not found")
        
        if flow.read_only:
            raise HTTPException(
                status_code=403, 
                detail="Forbidden. You do not have permission to modify this flow. It may be marked read-only."
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to check flow read-only status for %s: %s", flow_id, e)
        raise HTTPException(status_code=500, detail="Internal server error")

# HEAD endpoint
@router.head("/flows/{flow_id}/segments")
async def head_flow_segments(flow_id: str):
    """Return flow segments path headers"""
    return {}

# GET endpoint
@router.get("/flows/{flow_id}/segments", response_model=List[FlowSegment])
async def list_flow_segments(
    flow_id: str,
    timerange: Optional[str] = Query(None, description="Filter by time range"),
    store: VASTStore = Depends(get_vast_store)
):
    """List segments for a specific flow"""
    try:
        segments = await get_flow_segments(store, flow_id, timerange)
        return segments
    except Exception as e:
        logger.error("Failed to list segments for flow %s: %s", flow_id, e)
        raise HTTPException(status_code=500, detail="Internal server error")

# POST endpoint for creating flow segments (TAMS 7.0 compliant - metadata only)
@router.post("/flows/{flow_id}/segments", response_model=FlowSegment, status_code=201)
async def create_new_flow_segment(
    flow_id: str,
    segment: FlowSegment = Body(...),
    store: VASTStore = Depends(get_vast_store)
):
    """
    Create a new flow segment (TAMS 7.0 compliant)
    
    This endpoint registers segment metadata only. Media uploads are handled separately via:
    1. POST /flows/{flow_id}/storage - to get presigned URLs
    2. Upload media using those presigned URLs
    3. POST /flows/{flow_id}/segments - to register the segment metadata
    
    According to TAMS 7.0 specification, this endpoint does NOT handle file uploads.
    """
    try:
        await check_flow_read_only(store, flow_id)
        
        # Validate segment data
        if not segment.object_id:
            raise HTTPException(status_code=400, detail="object_id is required")
        if not segment.timerange:
            raise HTTPException(status_code=400, detail="timerange is required")
        
        # Generate storage_path if not provided to ensure consistency
        if not segment.storage_path:
            s3_store = S3Store()
            storage_path = s3_store.generate_segment_key(flow_id, segment.object_id, segment.timerange)
            segment.storage_path = storage_path
            logger.info("Generated storage_path for segment %s: %s", segment.object_id, storage_path)
        
        # Create segment metadata only (no media data)
        success = await create_flow_segment(store, flow_id, segment)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to create segment")
        
        # Generate get_urls dynamically since presigned URLs expire
        if segment.storage_path:
            try:
                s3_store = S3Store()
                get_urls = await s3_store.generate_get_urls(segment)
                segment.get_urls = get_urls
                logger.info("Generated dynamic get_urls for segment %s: %d URLs", 
                          segment.object_id, len(get_urls) if get_urls else 0)
            except Exception as e:
                logger.error("Failed to generate get_urls for segment %s: %s", 
                           segment.object_id, e)
                segment.get_urls = []
        else:
            logger.warning("No storage_path for segment %s, cannot generate get_urls", 
                         segment.object_id)
            segment.get_urls = []
        
        # Emit segment created event
        try:
            event_manager = EventManager(store)
            await event_manager.emit_segment_event('flows/segments_added', segment, flow_id=flow_id)
        except Exception as e:
            logger.warning("Failed to emit segment created event: %s", e)
        
        return segment
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to create flow segment for %s: %s", flow_id, e)
        raise HTTPException(status_code=500, detail="Internal server error")



# DELETE endpoint
@router.delete("/flows/{flow_id}/segments")
async def delete_flow_segments_by_id(
    flow_id: str,
    timerange: Optional[str] = Query(None, description="Time range to delete"),
    store: VASTStore = Depends(get_vast_store)
):
    """Delete segments for a flow (hard delete only - TAMS compliant)"""
    try:
        await check_flow_read_only(store, flow_id)
        
        # Get segments before deletion for event emission
        segments = await get_flow_segments(store, flow_id, timerange)
        
        success = await delete_flow_segments(store, flow_id, timerange)
        if not success:
            raise HTTPException(status_code=404, detail="Flow not found")
        
        # Emit segment deleted events
        if segments:
            try:
                event_manager = EventManager(store)
                for segment in segments:
                    await event_manager.emit_segment_event('flows/segments_deleted', segment)
            except Exception as e:
                logger.warning("Failed to emit segment deleted events: %s", e)
        
        return {"message": "Segments hard deleted successfully"}
        
    except ValueError as e:
        # ✅ NEW: Handle dependency violations with 409 Conflict
        logger.warning("Dependency violation deleting segments for flow %s: %s", flow_id, e)
        raise HTTPException(status_code=409, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete segments for flow %s: %s", flow_id, e)
        raise HTTPException(status_code=500, detail="Internal server error")

# Storage endpoint
@router.post("/flows/{flow_id}/storage", response_model=FlowStorage)
async def create_flow_storage_by_id(
    flow_id: str,
    storage_request: FlowStoragePost,
    store: VASTStore = Depends(get_vast_store)
):
    """Create storage allocation for a flow"""
    try:
        storage = await create_flow_storage(store, flow_id, storage_request)
        if not storage:
            raise HTTPException(status_code=404, detail="Flow not found")
        return storage
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to create storage for flow %s: %s", flow_id, e)
        raise HTTPException(status_code=500, detail="Internal server error") 