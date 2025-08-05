from fastapi import APIRouter, Depends, Query, Request, UploadFile, File, Form, HTTPException
from typing import List, Optional
from .models import FlowSegment, FlowStorage, FlowStoragePost
from .vast_store import VASTStore
from .dependencies import get_vast_store
from .segments import SegmentManager
import logging

router = APIRouter()
logger = logging.getLogger(__name__)
segment_manager = SegmentManager()

@router.head("/flows/{flow_id}/segments")
async def head_flow_segments(flow_id: str):
    """Return headers for the segments endpoint for a given flow."""
    logger.info(f"HEAD /flows/{flow_id}/segments called")
    return await segment_manager.head_segments(flow_id)

@router.get("/flows/{flow_id}/segments", response_model=List[FlowSegment])
async def get_flow_segments(
    flow_id: str,
    timerange: Optional[str] = Query(None, description="Filter by time range"),
    store: VASTStore = Depends(get_vast_store)
):
    """Get flow segments for a flow, optionally filtered by timerange."""
    logger.info(f"GET /flows/{flow_id}/segments called with timerange={timerange}")
    return await segment_manager.get_segments(flow_id, timerange, store)

@router.post("/flows/{flow_id}/segments", response_model=FlowSegment, status_code=201)
async def create_flow_segment(
    flow_id: str,
    request: Request,
    file: UploadFile = File(...),
    segment: str = Form(None),
    store: VASTStore = Depends(get_vast_store)
):
    """Create a new flow segment for a flow."""
    logger.info(f"POST /flows/{flow_id}/segments called")
    return await segment_manager.create_segment(flow_id, request, file, segment, store)

@router.delete("/flows/{flow_id}/segments")
async def delete_flow_segments(
    flow_id: str,
    timerange: Optional[str] = Query(None, description="Delete segments in time range"),
    soft_delete: bool = Query(True, description="Perform soft delete (default) or hard delete"),
    deleted_by: str = Query("system", description="User/system performing the deletion"),
    store: VASTStore = Depends(get_vast_store)
):
    """Delete flow segments for a flow, optionally filtered by timerange."""
    logger.info(f"DELETE /flows/{flow_id}/segments called with timerange={timerange}, soft_delete={soft_delete}")
    return await segment_manager.delete_segments(flow_id, timerange, store, soft_delete=soft_delete, deleted_by=deleted_by)

@router.post("/flows/{flow_id}/storage", response_model=FlowStorage)
async def allocate_flow_storage(
    flow_id: str,
    storage_request: FlowStoragePost,
    store: VASTStore = Depends(get_vast_store)
):
    """Allocate storage for flow segments."""
    logger.info(f"POST /flows/{flow_id}/storage called")
    return await segment_manager.allocate_storage(flow_id, storage_request, store) 