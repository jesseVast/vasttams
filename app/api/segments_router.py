from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from typing import List, Optional
from ..models.models import FlowSegment, FlowStorage, FlowStoragePost
from .segments import get_flow_segments, create_flow_segment, delete_flow_segments, create_flow_storage, SegmentManager
from ..storage.vast_store import VASTStore
from ..core.dependencies import get_vast_store
import logging
import json

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
        logger.error(f"Failed to check flow read-only status for {flow_id}: {e}")
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
        logger.error(f"Failed to list segments for flow {flow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# POST endpoint for segment data (JSON or multipart form)
@router.post("/flows/{flow_id}/segments", response_model=FlowSegment, status_code=201)
async def create_new_flow_segment(
    flow_id: str,
    segment: Optional[FlowSegment] = None,
    file: Optional[UploadFile] = File(None),
    segment_data: Optional[str] = Form(None),
    store: VASTStore = Depends(get_vast_store)
):
    """Create a new segment for a flow (supports both JSON and multipart form data)"""
    try:
        await check_flow_read_only(store, flow_id)
        
        # Handle multipart form data
        if file and segment_data:
            try:
                segment_json = json.loads(segment_data)
                segment_obj = FlowSegment(**segment_json)
            except json.JSONDecodeError as e:
                raise HTTPException(status_code=400, detail=f"Invalid JSON in segment data: {e}")
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Invalid segment data: {e}")
            
            # Read file content
            file_content = await file.read()
            
            # Create segment using the store
            success = await store.create_flow_segment(segment_obj, flow_id, file_content, file.content_type or "application/octet-stream")
            if not success:
                raise HTTPException(status_code=500, detail="Failed to create segment")
            
            return segment_obj
        
        # Handle JSON data
        elif segment:
            success = await create_flow_segment(store, flow_id, segment)
            if not success:
                raise HTTPException(status_code=500, detail="Failed to create segment")
            return segment
        
        # Handle form data without file (segment_data only)
        elif segment_data:
            try:
                segment_json = json.loads(segment_data)
                segment_obj = FlowSegment(**segment_json)
            except json.JSONDecodeError as e:
                raise HTTPException(status_code=400, detail=f"Invalid JSON in segment data: {e}")
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Invalid segment data: {e}")
            
            # Create segment without file data
            success = await create_flow_segment(store, flow_id, segment_obj)
            if not success:
                raise HTTPException(status_code=500, detail="Failed to create segment")
            
            return segment_obj
        else:
            raise HTTPException(status_code=400, detail="Either segment JSON or file upload with segment data is required")
            
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
        await check_flow_read_only(store, flow_id)
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