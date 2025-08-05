from fastapi import APIRouter, Depends, HTTPException, Query, Response
from typing import List, Optional, Union
from app.models import (
    Flow, FlowsResponse, FlowFilters, FlowDetailFilters, 
    VideoFlow, AudioFlow, DataFlow, ImageFlow, MultiFlow,
    FlowSegment, FlowSegmentFilters, FlowSegmentPost, FlowSegmentBulkFailure,
    FlowStoragePost, FlowStorage, PagingInfo
)
from app.flows import get_flow, create_flow, update_flow, delete_flow, get_flows
from app.segments import get_flow_segments, create_flow_segment, delete_flow_segments
from app.vast_store import VASTStore
from app.dependencies import get_vast_store
from app.auth import require_authentication
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# HEAD endpoints
@router.head("/flows")
async def head_flows():
    """Return flows path headers"""
    return {}

@router.head("/flows/{flow_id}")
async def head_flow(flow_id: str):
    """Return flow path headers"""
    return {}

@router.head("/flows/{flow_id}/segments")
async def head_flow_segments(flow_id: str):
    """Return flow segments path headers"""
    return {}

@router.head("/flows/{flow_id}/storage")
async def head_flow_storage(flow_id: str):
    """Return flow storage path headers"""
    return {}

# GET endpoints
@router.get("/flows", response_model=FlowsResponse)
async def get_flows(
    source_id: Optional[str] = Query(None, description="Filter by source ID"),
    timerange: Optional[str] = Query(None, description="Filter by time range"),
    format: Optional[str] = Query(None, description="Filter by format"),
    codec: Optional[str] = Query(None, description="Filter by codec"),
    label: Optional[str] = Query(None, description="Filter by label"),
    frame_width: Optional[int] = Query(None, description="Filter by frame width"),
    frame_height: Optional[int] = Query(None, description="Filter by frame height"),
    page: Optional[str] = Query(None, description="Pagination key"),
    limit: Optional[int] = Query(None, ge=1, le=1000, description="Number of items per page"),
    store: VASTStore = Depends(get_vast_store),
    current_user: dict = Depends(require_authentication)
):
    """List flows with filtering and pagination"""
    try:
        filters = FlowFilters(
            source_id=source_id,
            timerange=timerange,
            format=format,
            codec=codec,
            label=label,
            frame_width=frame_width,
            frame_height=frame_height,
            page=page,
            limit=limit
        )
        
        flows = await get_flows(store, filters)
        
        # Add pagination headers if needed
        response = FlowsResponse(data=flows)
        if page and limit:
            response.paging = PagingInfo(limit=limit, next_key=page)
            
        return response
        
    except Exception as e:
        logger.error(f"Failed to list flows: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/flows/{flow_id}", response_model=Flow)
async def get_flow_by_id(
    flow_id: str,
    include_timerange: bool = Query(False, description="Include timerange in response"),
    timerange: Optional[str] = Query(None, description="Filter by time range"),
    accept_get_urls: Optional[str] = Query(None, description="Filter URLs by label"),
    accept_storage_ids: Optional[str] = Query(None, description="Filter by storage backend IDs"),
    presigned: Optional[bool] = Query(None, description="Filter by presigned status"),
    verbose_storage: Optional[bool] = Query(False, description="Include storage metadata"),
    store: VASTStore = Depends(get_vast_store)
):
    """Get a specific flow by ID with enhanced filtering"""
    try:
        filters = FlowDetailFilters(
            include_timerange=include_timerange,
            timerange=timerange,
            accept_get_urls=accept_get_urls,
            accept_storage_ids=accept_storage_ids,
            presigned=presigned,
            verbose_storage=verbose_storage
        )
        
        flow = await get_flow(store, flow_id, filters)
        if not flow:
            raise HTTPException(status_code=404, detail="Flow not found")
        return flow
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get flow {flow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/flows/{flow_id}/segments", response_model=List[FlowSegment])
async def get_flow_segments_by_id(
    flow_id: str,
    timerange: Optional[str] = Query(None, description="Filter by time range"),
    object_id: Optional[str] = Query(None, description="Filter by object ID"),
    accept_get_urls: Optional[str] = Query(None, description="Filter URLs by label"),
    accept_storage_ids: Optional[str] = Query(None, description="Filter by storage backend IDs"),
    presigned: Optional[bool] = Query(None, description="Filter by presigned status"),
    verbose_storage: Optional[bool] = Query(False, description="Include storage metadata"),
    store: VASTStore = Depends(get_vast_store)
):
    """Get flow segments with enhanced filtering"""
    try:
        filters = FlowSegmentFilters(
            timerange=timerange,
            object_id=object_id,
            accept_get_urls=accept_get_urls,
            accept_storage_ids=accept_storage_ids,
            presigned=presigned,
            verbose_storage=verbose_storage
        )
        
        segments = await get_flow_segments(store, flow_id, filters)
        return segments
        
    except Exception as e:
        logger.error(f"Failed to get flow segments for {flow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# POST endpoints
@router.post("/flows", response_model=Flow, status_code=201)
async def create_new_flow(
    flow: Flow,
    store: VASTStore = Depends(get_vast_store),
    current_user: dict = Depends(require_authentication)
):
    """Create a new flow"""
    try:
        success = await create_flow(store, flow)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to create flow")
        return flow
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create flow: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/flows/{flow_id}/segments", response_model=Union[FlowSegment, FlowSegmentBulkFailure], status_code=201)
async def create_flow_segment(
    flow_id: str,
    segment: Union[FlowSegmentPost, List[FlowSegmentPost]],
    store: VASTStore = Depends(get_vast_store)
):
    """Create flow segment(s) with bulk support"""
    try:
        if isinstance(segment, list):
            # Bulk creation
            failed_segments = []
            success_count = 0
            
            for seg in segment:
                try:
                    success = await create_flow_segment(store, flow_id, seg)
                    if success:
                        success_count += 1
                    else:
                        failed_segments.append({"segment": seg.dict(), "error": "Failed to create segment"})
                except Exception as e:
                    failed_segments.append({"segment": seg.dict(), "error": str(e)})
            
            if failed_segments:
                # Return 200 with failure details
                return FlowSegmentBulkFailure(
                    failed_segments=failed_segments,
                    error_count=len(failed_segments),
                    total_count=len(segment)
                )
            else:
                # All successful, return 201
                return segment[0] if len(segment) == 1 else {"message": f"Created {len(segment)} segments"}
        else:
            # Single segment creation
            success = await create_flow_segment(store, flow_id, segment)
            if not success:
                raise HTTPException(status_code=400, detail="Failed to create segment")
            return segment
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create flow segment for {flow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/flows/{flow_id}/storage", response_model=FlowStorage, status_code=201)
async def allocate_flow_storage(
    flow_id: str,
    storage_request: FlowStoragePost,
    store: VASTStore = Depends(get_vast_store)
):
    """Allocate storage for flow"""
    try:
        # This would integrate with the storage backend
        # For now, return a mock response
        storage_locations = [
            {
                "object_id": f"{flow_id}_obj_1",
                "put_url": f"https://storage.example.com/upload/{flow_id}_obj_1",
                "bucket_put_url": f"https://storage.example.com/bucket/{flow_id}"
            }
        ]
        return FlowStorage(storage_locations=storage_locations)
        
    except Exception as e:
        logger.error(f"Failed to allocate storage for flow {flow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# PUT endpoints
@router.put("/flows/{flow_id}", response_model=Flow)
async def update_flow_by_id(
    flow_id: str,
    flow: Flow,
    store: VASTStore = Depends(get_vast_store)
):
    """Update a flow"""
    try:
        success = await update_flow(store, flow_id, flow)
        if not success:
            raise HTTPException(status_code=404, detail="Flow not found")
        return flow
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update flow {flow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# DELETE endpoints
@router.delete("/flows/{flow_id}")
async def delete_flow_by_id(
    flow_id: str,
    store: VASTStore = Depends(get_vast_store),
    current_user: dict = Depends(require_authentication)
):
    """Delete a flow"""
    try:
        success = await delete_flow(store, flow_id)
        if not success:
            raise HTTPException(status_code=404, detail="Flow not found")
        return {"message": "Flow deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete flow {flow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/flows/{flow_id}/segments")
async def delete_flow_segments(
    flow_id: str,
    timerange: Optional[str] = Query(None, description="Filter by time range"),
    object_id: Optional[str] = Query(None, description="Filter by object ID"),
    store: VASTStore = Depends(get_vast_store)
):
    """Delete flow segments with async support"""
    try:
        success = await delete_flow_segments(store, flow_id, timerange, object_id)
        if not success:
            raise HTTPException(status_code=404, detail="Flow not found")
        return {"message": "Flow segments deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete flow segments for {flow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Individual field endpoints
@router.head("/flows/{flow_id}/label")
async def head_flow_label(flow_id: str):
    """Return flow label path headers"""
    return {}

@router.get("/flows/{flow_id}/label")
async def get_flow_label(
    flow_id: str,
    store: VASTStore = Depends(get_vast_store)
):
    """Get flow label"""
    try:
        flow = await get_flow(store, flow_id)
        if not flow:
            raise HTTPException(status_code=404, detail="Flow not found")
        return {"label": flow.label}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get flow label for {flow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/flows/{flow_id}/label")
async def update_flow_label(
    flow_id: str,
    label: str,
    store: VASTStore = Depends(get_vast_store)
):
    """Update flow label"""
    try:
        flow = await get_flow(store, flow_id)
        if not flow:
            raise HTTPException(status_code=404, detail="Flow not found")
        
        flow.label = label
        success = await update_flow(store, flow_id, flow)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update flow label")
        
        return {"label": label}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update flow label for {flow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Individual field endpoints - Tags
@router.head("/flows/{flow_id}/tags")
async def head_flow_tags(flow_id: str):
    """Return flow tags path headers"""
    return {}

@router.get("/flows/{flow_id}/tags")
async def get_flow_tags(
    flow_id: str,
    store: VASTStore = Depends(get_vast_store)
):
    """Get flow tags"""
    try:
        flow = await get_flow(store, flow_id)
        if not flow:
            raise HTTPException(status_code=404, detail="Flow not found")
        return flow.tags or {}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get flow tags for {flow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.head("/flows/{flow_id}/tags/{name}")
async def head_flow_tag(flow_id: str, name: str):
    """Return flow tag path headers"""
    return {}

@router.get("/flows/{flow_id}/tags/{name}")
async def get_flow_tag(
    flow_id: str,
    name: str,
    store: VASTStore = Depends(get_vast_store)
):
    """Get flow tag by name"""
    try:
        flow = await get_flow(store, flow_id)
        if not flow:
            raise HTTPException(status_code=404, detail="Flow not found")
        
        if not flow.tags or name not in flow.tags:
            raise HTTPException(status_code=404, detail="Tag not found")
        
        return {"name": name, "value": flow.tags[name]}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get flow tag {name} for {flow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/flows/{flow_id}/tags/{name}")
async def update_flow_tag(
    flow_id: str,
    name: str,
    value: str,
    store: VASTStore = Depends(get_vast_store)
):
    """Update flow tag"""
    try:
        flow = await get_flow(store, flow_id)
        if not flow:
            raise HTTPException(status_code=404, detail="Flow not found")
        
        # Update the tag
        if not flow.tags:
            flow.tags = {}
        flow.tags[name] = value
        
        # Save the updated flow
        success = await update_flow(store, flow_id, flow)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update flow tag")
        
        return {"message": "Tag updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update flow tag {name} for {flow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/flows/{flow_id}/tags/{name}")
async def delete_flow_tag(
    flow_id: str,
    name: str,
    store: VASTStore = Depends(get_vast_store)
):
    """Delete flow tag"""
    try:
        flow = await get_flow(store, flow_id)
        if not flow:
            raise HTTPException(status_code=404, detail="Flow not found")
        
        if not flow.tags or name not in flow.tags:
            raise HTTPException(status_code=404, detail="Tag not found")
        
        del flow.tags[name]
        success = await update_flow(store, flow_id, flow)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete flow tag")
        
        return {"message": "Tag deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete flow tag {name} for {flow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Individual field endpoints - Description
@router.head("/flows/{flow_id}/description")
async def head_flow_description(flow_id: str):
    """Return flow description path headers"""
    return {}

@router.get("/flows/{flow_id}/description")
async def get_flow_description(
    flow_id: str,
    store: VASTStore = Depends(get_vast_store)
):
    """Get flow description"""
    try:
        flow = await get_flow(store, flow_id)
        if not flow:
            raise HTTPException(status_code=404, detail="Flow not found")
        return {"description": flow.description or ""}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get flow description for {flow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/flows/{flow_id}/description")
async def update_flow_description(
    flow_id: str,
    description: str,
    store: VASTStore = Depends(get_vast_store)
):
    """Update flow description"""
    try:
        flow = await get_flow(store, flow_id)
        if not flow:
            raise HTTPException(status_code=404, detail="Flow not found")
        
        flow.description = description
        success = await update_flow(store, flow_id, flow)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update flow description")
        
        return {"description": description}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update flow description for {flow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Individual field endpoints - Read Only
@router.head("/flows/{flow_id}/read_only")
async def head_flow_read_only(flow_id: str):
    """Return flow read_only path headers"""
    return {}

@router.get("/flows/{flow_id}/read_only")
async def get_flow_read_only(
    flow_id: str,
    store: VASTStore = Depends(get_vast_store)
):
    """Get flow read_only status"""
    try:
        flow = await get_flow(store, flow_id)
        if not flow:
            raise HTTPException(status_code=404, detail="Flow not found")
        return {"read_only": flow.read_only}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get flow read_only for {flow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/flows/{flow_id}/read_only")
async def update_flow_read_only(
    flow_id: str,
    read_only: bool,
    store: VASTStore = Depends(get_vast_store)
):
    """Update flow read_only status"""
    try:
        flow = await get_flow(store, flow_id)
        if not flow:
            raise HTTPException(status_code=404, detail="Flow not found")
        
        flow.read_only = read_only
        success = await update_flow(store, flow_id, flow)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update flow read_only")
        
        return {"read_only": read_only}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update flow read_only for {flow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Individual field endpoints - Flow Collection
@router.head("/flows/{flow_id}/flow_collection")
async def head_flow_collection(flow_id: str):
    """Return flow collection path headers"""
    return {}

@router.get("/flows/{flow_id}/flow_collection")
async def get_flow_collection(
    flow_id: str,
    store: VASTStore = Depends(get_vast_store)
):
    """Get flow collection"""
    try:
        flow = await get_flow(store, flow_id)
        if not flow:
            raise HTTPException(status_code=404, detail="Flow not found")
        return {"flow_collection": flow.flow_collection or []}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get flow collection for {flow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/flows/{flow_id}/flow_collection")
async def update_flow_collection(
    flow_id: str,
    flow_collection: List[str],
    store: VASTStore = Depends(get_vast_store)
):
    """Update flow collection"""
    try:
        flow = await get_flow(store, flow_id)
        if not flow:
            raise HTTPException(status_code=404, detail="Flow not found")
        
        flow.flow_collection = flow_collection
        success = await update_flow(store, flow_id, flow)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update flow collection")
        
        return {"flow_collection": flow_collection}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update flow collection for {flow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Individual field endpoints - Max Bit Rate
@router.head("/flows/{flow_id}/max_bit_rate")
async def head_flow_max_bit_rate(flow_id: str):
    """Return flow max_bit_rate path headers"""
    return {}

@router.get("/flows/{flow_id}/max_bit_rate")
async def get_flow_max_bit_rate(
    flow_id: str,
    store: VASTStore = Depends(get_vast_store)
):
    """Get flow max bit rate"""
    try:
        flow = await get_flow(store, flow_id)
        if not flow:
            raise HTTPException(status_code=404, detail="Flow not found")
        return {"max_bit_rate": flow.max_bit_rate}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get flow max_bit_rate for {flow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/flows/{flow_id}/max_bit_rate")
async def update_flow_max_bit_rate(
    flow_id: str,
    max_bit_rate: int,
    store: VASTStore = Depends(get_vast_store)
):
    """Update flow max bit rate"""
    try:
        flow = await get_flow(store, flow_id)
        if not flow:
            raise HTTPException(status_code=404, detail="Flow not found")
        
        flow.max_bit_rate = max_bit_rate
        success = await update_flow(store, flow_id, flow)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update flow max_bit_rate")
        
        return {"max_bit_rate": max_bit_rate}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update flow max_bit_rate for {flow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Individual field endpoints - Average Bit Rate
@router.head("/flows/{flow_id}/avg_bit_rate")
async def head_flow_avg_bit_rate(flow_id: str):
    """Return flow avg_bit_rate path headers"""
    return {}

@router.get("/flows/{flow_id}/avg_bit_rate")
async def get_flow_avg_bit_rate(
    flow_id: str,
    store: VASTStore = Depends(get_vast_store)
):
    """Get flow average bit rate"""
    try:
        flow = await get_flow(store, flow_id)
        if not flow:
            raise HTTPException(status_code=404, detail="Flow not found")
        return {"avg_bit_rate": flow.avg_bit_rate}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get flow avg_bit_rate for {flow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/flows/{flow_id}/avg_bit_rate")
async def update_flow_avg_bit_rate(
    flow_id: str,
    avg_bit_rate: int,
    store: VASTStore = Depends(get_vast_store)
):
    """Update flow average bit rate"""
    try:
        flow = await get_flow(store, flow_id)
        if not flow:
            raise HTTPException(status_code=404, detail="Flow not found")
        
        flow.avg_bit_rate = avg_bit_rate
        success = await update_flow(store, flow_id, flow)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update flow avg_bit_rate")
        
        return {"avg_bit_rate": avg_bit_rate}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update flow avg_bit_rate for {flow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error") 