from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from app.models import FlowSegment, FlowStorage, FlowStoragePost
from app.segments import get_flow_segments, create_flow_segment, delete_flow_segments, create_flow_storage
from app.vast_store import VASTStore
from app.dependencies import get_vast_store
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

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
        logger.error(f"Failed to list segments for flow {flow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# POST endpoint
@router.post("/flows/{flow_id}/segments", response_model=FlowSegment, status_code=201)
async def create_new_flow_segment(
    flow_id: str,
    segment: FlowSegment,
    store: VASTStore = Depends(get_vast_store)
):
    """Create a new segment for a flow"""
    try:
        success = await create_flow_segment(store, flow_id, segment)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to create segment")
        return segment
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create segment for flow {flow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# DELETE endpoint
@router.delete("/flows/{flow_id}/segments")
async def delete_flow_segments_by_id(
    flow_id: str,
    timerange: Optional[str] = Query(None, description="Time range to delete"),
    soft_delete: bool = Query(True, description="Use soft delete"),
    deleted_by: str = Query("system", description="User performing the deletion"),
    store: VASTStore = Depends(get_vast_store)
):
    """Delete segments for a flow"""
    try:
        success = await delete_flow_segments(store, flow_id, timerange, soft_delete, deleted_by)
        if not success:
            raise HTTPException(status_code=404, detail="Flow not found")
        return {"message": "Segments deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete segments for flow {flow_id}: {e}")
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
        logger.error(f"Failed to create storage for flow {flow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error") 