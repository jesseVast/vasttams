from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form, Body, Request
from typing import List, Optional, Dict, Any
from app.models import FlowSegment, FlowStorage, FlowStoragePost, SegmentFilters
from app.segments import get_flow_segments, create_flow_segment, delete_flow_segments, create_flow_storage, SegmentManager
from app.vast_store import VASTStore
from app.dependencies import get_vast_store
from app.core.event_manager import EventManager
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
    request: Request = None,  # To access all query parameters for tag filtering
    store: VASTStore = Depends(get_vast_store)
):
    """List segments for a specific flow with optional tag filtering"""
    try:
        # Parse tag filters from query parameters
        tag_filters = {}
        tag_exists_filters = {}
        
        if request:
            query_params = dict(request.query_params)
            for key, value in query_params.items():
                if key.startswith('tag.'):
                    tag_name = key[4:]  # Remove 'tag.' prefix
                    tag_filters[tag_name] = value
                elif key.startswith('tag_exists.'):
                    tag_name = key[11:]  # Remove 'tag_exists.' prefix
                    tag_exists_filters[tag_name] = value.lower() == 'true'
        
        filters = SegmentFilters(
            timerange=timerange,
            tag_filters=tag_filters if tag_filters else None,
            tag_exists_filters=tag_exists_filters if tag_exists_filters else None
        )
        
        segments = await get_flow_segments(store, flow_id, filters)
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
            
            # Emit webhook event for segment creation
            try:
                event_manager = EventManager(store)
                await event_manager.emit_segment_event('flows/segments_added', segment_obj, flow_id=flow_id)
            except Exception as e:
                logger.warning(f"Failed to emit webhook event: {e}")
            
            return segment_obj
        
        # Handle JSON data
        elif segment:
            success = await create_flow_segment(store, flow_id, segment)
            if not success:
                raise HTTPException(status_code=500, detail="Failed to create segment")
            
            # Emit webhook event for segment creation
            try:
                event_manager = EventManager(store)
                await event_manager.emit_segment_event('flows/segments_added', segment, flow_id=flow_id)
            except Exception as e:
                logger.warning(f"Failed to emit webhook event: {e}")
            
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
            
            # Emit webhook event for segment creation
            try:
                event_manager = EventManager(store)
                await event_manager.emit_segment_event('flows/segments_added', segment_obj, flow_id=flow_id)
            except Exception as e:
                logger.warning(f"Failed to emit webhook event: {e}")
            
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


# Segment tag endpoints
@router.get("/flows/{flow_id}/segments/{segment_id}/tags")
async def get_segment_tags(
    flow_id: str,
    segment_id: str,
    store: VASTStore = Depends(get_vast_store)
):
    """Get all tags for a segment"""
    try:
        # Verify segment exists
        segments = await store.get_flow_segments(flow_id)
        segment_exists = any(seg.object_id == segment_id for seg in segments)
        if not segment_exists:
            raise HTTPException(status_code=404, detail="Segment not found")
        
        tags = await store.get_segment_tags(segment_id)
        return tags or {}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get segment tags for {segment_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/flows/{flow_id}/segments/{segment_id}/tags/{name}")
async def get_segment_tag(
    flow_id: str,
    segment_id: str,
    name: str,
    store: VASTStore = Depends(get_vast_store)
):
    """Get specific segment tag value"""
    try:
        # Verify segment exists
        segments = await store.get_flow_segments(flow_id)
        segment_exists = any(seg.object_id == segment_id for seg in segments)
        if not segment_exists:
            raise HTTPException(status_code=404, detail="Segment not found")
        
        tags = await store.get_segment_tags(segment_id)
        if not tags or name not in tags:
            raise HTTPException(status_code=404, detail="Tag not found")
        
        return {name: tags[name]}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get segment tag {name} for {segment_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/flows/{flow_id}/segments/{segment_id}/tags/{name}")
async def update_segment_tag(
    flow_id: str,
    segment_id: str,
    name: str,
    value: str = Body(..., description="Tag value"),
    store: VASTStore = Depends(get_vast_store)
):
    """Create or update segment tag"""
    try:
        await check_flow_read_only(store, flow_id)
        
        # Verify segment exists
        segments = await store.get_flow_segments(flow_id)
        segment_exists = any(seg.object_id == segment_id for seg in segments)
        if not segment_exists:
            raise HTTPException(status_code=404, detail="Segment not found")
        
        success = await store.update_segment_tag(segment_id, name, value)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update segment tag")
        
        return {"message": "Tag updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update segment tag {name} for {segment_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/flows/{flow_id}/segments/{segment_id}/tags/{name}")
async def delete_segment_tag(
    flow_id: str,
    segment_id: str,
    name: str,
    store: VASTStore = Depends(get_vast_store)
):
    """Delete specific segment tag"""
    try:
        await check_flow_read_only(store, flow_id)
        
        # Verify segment exists
        segments = await store.get_flow_segments(flow_id)
        segment_exists = any(seg.object_id == segment_id for seg in segments)
        if not segment_exists:
            raise HTTPException(status_code=404, detail="Segment not found")
        
        success = await store.delete_segment_tag(segment_id, name)
        if not success:
            raise HTTPException(status_code=404, detail="Tag not found")
        
        return {"message": "Tag deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete segment tag {name} for {segment_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/flows/{flow_id}/segments/{segment_id}/tags")
async def delete_segment_tags(
    flow_id: str,
    segment_id: str,
    store: VASTStore = Depends(get_vast_store)
):
    """Delete all tags for a segment"""
    try:
        await check_flow_read_only(store, flow_id)
        
        # Verify segment exists
        segments = await store.get_flow_segments(flow_id)
        segment_exists = any(seg.object_id == segment_id for seg in segments)
        if not segment_exists:
            raise HTTPException(status_code=404, detail="Segment not found")
        
        success = await store.delete_segment_tags(segment_id)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete segment tags")
        
        return {"message": "All tags deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete segment tags for {segment_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error") 