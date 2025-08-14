from fastapi import APIRouter, Depends, HTTPException, Query, Body
from typing import List, Optional
import uuid
from ..models.models import Flow, FlowsResponse, FlowFilters, FlowDetailFilters, Tags, FlowStoragePost, FlowStorage, HttpRequest, MediaObject
from .flows import get_flows, get_flow, create_flow, update_flow, delete_flow
from ..storage.vast_store import VASTStore
from ..core.dependencies import get_vast_store
from ..core.config import get_settings
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
        logger.error(f"Failed to check flow read-only status for {flow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# HEAD endpoints
@router.head("/flows")
async def head_flows():
    """Return flows path headers"""
    return {}

@router.options("/flows")
async def options_flows():
    """Flows endpoint OPTIONS method for CORS preflight"""
    return {}

@router.head("/flows/{flow_id}")
async def head_flow(flow_id: str):
    """Return flow path headers"""
    return {}

# GET endpoints
@router.get("/flows", response_model=FlowsResponse)
async def list_flows(
    source_id: Optional[str] = Query(None, description="Filter by source ID"),
    timerange: Optional[str] = Query(None, description="Filter by time range"),
    format: Optional[str] = Query(None, description="Filter by format"),
    codec: Optional[str] = Query(None, description="Filter by codec"),
    label: Optional[str] = Query(None, description="Filter by label"),
    frame_width: Optional[int] = Query(None, description="Filter by frame width"),
    frame_height: Optional[int] = Query(None, description="Filter by frame height"),
    page: Optional[str] = Query(None, description="Pagination key"),
    limit: Optional[int] = Query(100, ge=1, le=1000, description="Number of results to return"),
    store: VASTStore = Depends(get_vast_store)
):
    """List flows with optional filtering"""
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
        return FlowsResponse(data=flows)
    except Exception as e:
        logger.error(f"Failed to list flows: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/flows/{flow_id}", response_model=Flow)
async def get_flow_by_id(
    flow_id: str,
    include_timerange: bool = Query(False, description="Include timerange in response"),
    timerange: Optional[str] = Query(None, description="Filter by time range"),
    store: VASTStore = Depends(get_vast_store)
):
    """Get a specific flow by ID"""
    try:
        filters = FlowDetailFilters(include_timerange=include_timerange, timerange=timerange)
        flow = await get_flow(store, flow_id, filters)
        if not flow:
            raise HTTPException(status_code=404, detail="Flow not found")
        return flow
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get flow {flow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# PUT endpoint
@router.put("/flows/{flow_id}", response_model=Flow)
async def update_flow_by_id(
    flow_id: str,
    flow: Flow,
    store: VASTStore = Depends(get_vast_store)
):
    """Update a flow"""
    try:
        await check_flow_read_only(store, flow_id)
        updated_flow = await update_flow(store, flow_id, flow)
        if not updated_flow:
            raise HTTPException(status_code=404, detail="Flow not found")
        return updated_flow
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update flow {flow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# DELETE endpoint
@router.delete("/flows/{flow_id}")
async def delete_flow_by_id(
    flow_id: str,
    soft_delete: bool = Query(True, description="Use soft delete"),
    cascade: bool = Query(True, description="Cascade delete related segments"),
    deleted_by: str = Query("system", description="User performing the deletion"),
    store: VASTStore = Depends(get_vast_store)
):
    """Delete a flow"""
    try:
        await check_flow_read_only(store, flow_id)
        success = await delete_flow(store, flow_id, soft_delete, cascade, deleted_by)
        if not success:
            raise HTTPException(status_code=404, detail="Flow not found")
        return {"message": "Flow deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete flow {flow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# POST endpoint
@router.post("/flows", response_model=Flow, status_code=201)
async def create_new_flow(
    flow: Flow,
    store: VASTStore = Depends(get_vast_store)
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

# Batch POST endpoint
@router.post("/flows/batch", response_model=List[Flow], status_code=201)
async def create_flows_batch(
    flows: List[Flow],
    store: VASTStore = Depends(get_vast_store)
):
    """Create multiple flows in a single batch operation using VAST's native batch insert"""
    try:
        # Convert Pydantic models to dictionaries for batch insert
        flow_data = []
        for flow in flows:
            flow_dict = flow.model_dump()
            flow_data.append(flow_dict)
        
        # Use VAST's native batch insert functionality
        success = await store.db_manager.insert_batch_efficient(
            table_name="flows",
            data=flow_data,
            batch_size=len(flow_data)
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to insert flows batch")
        
        logger.info(f"Successfully created {len(flows)} flows using VAST batch insert")
        return flows
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create flows batch: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Individual field endpoints
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
        return flow.tags.root if flow.tags else {}
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
    """Get specific flow tag value"""
    try:
        flow = await get_flow(store, flow_id)
        if not flow:
            raise HTTPException(status_code=404, detail="Flow not found")
        if not flow.tags or name not in flow.tags:
            raise HTTPException(status_code=404, detail="Tag not found")
        return flow.tags[name]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get flow tag {name} for {flow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/flows/{flow_id}/tags/{name}")
async def update_flow_tag(
    flow_id: str,
    name: str,
    value: str = Body(..., description="Tag value"),
    store: VASTStore = Depends(get_vast_store)
):
    """Create or update flow tag"""
    try:
        await check_flow_read_only(store, flow_id)
        flow = await get_flow(store, flow_id)
        if not flow:
            raise HTTPException(status_code=404, detail="Flow not found")
        
        # Update the tag
        if not flow.tags:
            flow.tags = {}
        flow.tags[name] = value
        
        # Save the updated flow
        success = await store.update_flow(flow_id, flow)
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
    """Delete specific flow tag"""
    try:
        await check_flow_read_only(store, flow_id)
        flow = await get_flow(store, flow_id)
        if not flow:
            raise HTTPException(status_code=404, detail="Flow not found")
        
        if not flow.tags or name not in flow.tags:
            raise HTTPException(status_code=404, detail="Tag not found")
        
        # Remove the tag
        if flow.tags and name in flow.tags:
            # Create a new dict without the deleted tag
            new_tags = dict(flow.tags.root)
            del new_tags[name]
            flow.tags = Tags(root=new_tags)
        
        # Save the updated flow
        success = await store.update_flow(flow_id, flow)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete flow tag")
        
        return {"message": "Tag deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete flow tag {name} for {flow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

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
        return flow.description or ""
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
        await check_flow_read_only(store, flow_id)
        flow = await get_flow(store, flow_id)
        if not flow:
            raise HTTPException(status_code=404, detail="Flow not found")
        
        flow.description = description
        success = await store.update_flow(flow_id, flow)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update flow description")
        
        return {"message": "Description updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update flow description for {flow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/flows/{flow_id}/description")
async def delete_flow_description(
    flow_id: str,
    store: VASTStore = Depends(get_vast_store)
):
    """Delete flow description"""
    try:
        await check_flow_read_only(store, flow_id)
        flow = await get_flow(store, flow_id)
        if not flow:
            raise HTTPException(status_code=404, detail="Flow not found")
        
        flow.description = None
        
        # Save the updated flow
        success = await store.update_flow(flow_id, flow)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete flow description")
        
        return {"message": "Description deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete flow description for {flow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

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
        return flow.label or ""
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
        await check_flow_read_only(store, flow_id)
        flow = await get_flow(store, flow_id)
        if not flow:
            raise HTTPException(status_code=404, detail="Flow not found")
        
        flow.label = label
        success = await store.update_flow(flow_id, flow)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update flow label")
        
        return {"message": "Label updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update flow label for {flow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/flows/{flow_id}/label")
async def delete_flow_label(
    flow_id: str,
    store: VASTStore = Depends(get_vast_store)
):
    """Delete flow label"""
    try:
        await check_flow_read_only(store, flow_id)
        flow = await get_flow(store, flow_id)
        if not flow:
            raise HTTPException(status_code=404, detail="Flow not found")
        
        flow.label = None
        
        # Save the updated flow
        success = await store.update_flow(flow_id, flow)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete flow label")
        
        return {"message": "Label deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete flow label for {flow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.head("/flows/{flow_id}/read_only")
async def head_flow_read_only(flow_id: str):
    """Return flow read-only path headers"""
    return {}

@router.get("/flows/{flow_id}/read_only")
async def get_flow_read_only(
    flow_id: str,
    store: VASTStore = Depends(get_vast_store)
):
    """Get flow read-only status"""
    try:
        flow = await get_flow(store, flow_id)
        if not flow:
            raise HTTPException(status_code=404, detail="Flow not found")
        return flow.read_only or False
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get flow read-only status for {flow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")



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
        
        # Only MultiFlow has flow_collection
        if hasattr(flow, 'flow_collection'):
            return flow.flow_collection
        else:
            return []
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
        await check_flow_read_only(store, flow_id)
        flow = await get_flow(store, flow_id)
        if not flow:
            raise HTTPException(status_code=404, detail="Flow not found")
        
        # Only MultiFlow can have flow_collection
        if hasattr(flow, 'flow_collection'):
            flow.flow_collection = flow_collection
            success = await store.update_flow(flow_id, flow)
            if not success:
                raise HTTPException(status_code=500, detail="Failed to update flow collection")
            return {"message": "Flow collection updated successfully"}
        else:
            raise HTTPException(status_code=400, detail="Flow type does not support flow collection")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update flow collection for {flow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.head("/flows/{flow_id}/max_bit_rate")
async def head_flow_max_bit_rate(flow_id: str):
    """Return flow max bit rate path headers"""
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
        
        # Check if flow has max_bit_rate field
        if hasattr(flow, 'max_bit_rate'):
            return flow.max_bit_rate
        else:
            raise HTTPException(status_code=404, detail="Max bit rate not available for this flow type")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get flow max bit rate for {flow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/flows/{flow_id}/max_bit_rate")
async def update_flow_max_bit_rate(
    flow_id: str,
    max_bit_rate: int,
    store: VASTStore = Depends(get_vast_store)
):
    """Update flow max bit rate"""
    try:
        await check_flow_read_only(store, flow_id)
        flow = await get_flow(store, flow_id)
        if not flow:
            raise HTTPException(status_code=404, detail="Flow not found")
        
        # Check if flow has max_bit_rate field
        if hasattr(flow, 'max_bit_rate'):
            flow.max_bit_rate = max_bit_rate
            success = await store.update_flow(flow_id, flow)
            if not success:
                raise HTTPException(status_code=500, detail="Failed to update flow max bit rate")
            return {"message": "Max bit rate updated successfully"}
        else:
            raise HTTPException(status_code=400, detail="Flow type does not support max bit rate")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update flow max bit rate for {flow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.head("/flows/{flow_id}/avg_bit_rate")
async def head_flow_avg_bit_rate(flow_id: str):
    """Return flow average bit rate path headers"""
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
        
        # Check if flow has avg_bit_rate field
        if hasattr(flow, 'avg_bit_rate'):
            return flow.avg_bit_rate
        else:
            raise HTTPException(status_code=404, detail="Average bit rate not available for this flow type")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get flow average bit rate for {flow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/flows/{flow_id}/avg_bit_rate")
async def update_flow_avg_bit_rate(
    flow_id: str,
    avg_bit_rate: int,
    store: VASTStore = Depends(get_vast_store)
):
    """Update flow average bit rate"""
    try:
        await check_flow_read_only(store, flow_id)
        flow = await get_flow(store, flow_id)
        if not flow:
            raise HTTPException(status_code=404, detail="Flow not found")
        
        # Check if flow has avg_bit_rate field
        if hasattr(flow, 'avg_bit_rate'):
            flow.avg_bit_rate = avg_bit_rate
            success = await store.update_flow(flow_id, flow)
            if not success:
                raise HTTPException(status_code=500, detail="Failed to update flow average bit rate")
            return {"message": "Average bit rate updated successfully"}
        else:
            raise HTTPException(status_code=400, detail="Flow type does not support average bit rate")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update flow average bit rate for {flow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Flow storage allocation endpoint
@router.post("/flows/{flow_id}/storage", response_model=FlowStorage, status_code=201)
async def allocate_flow_storage(
    flow_id: str,
    request: FlowStoragePost,
    store: VASTStore = Depends(get_vast_store)
):
    """Allocate storage locations for writing media objects"""
    try:
        # Check if flow exists
        flow = await get_flow(store, flow_id)
        if not flow:
            raise HTTPException(status_code=404, detail="Flow not found")
        
        # Check if flow is read-only
        await check_flow_read_only(store, flow_id)
        
        # Get settings for S3 configuration
        settings = get_settings()
        
        # Generate object IDs if not provided
        if request.object_ids:
            object_ids = request.object_ids
        else:
            # Generate the requested number of object IDs
            limit = request.limit or 10
            object_ids = [str(uuid.uuid4()) for _ in range(limit)]
        
        # Validate that object IDs don't already exist
        for object_id in object_ids:
            existing_object = await store.get_object(object_id)
            if existing_object:
                raise HTTPException(status_code=400, detail=f"Object ID {object_id} already exists")
        
        # Generate storage locations with pre-signed URLs
        media_objects = []
        for object_id in object_ids:
            # Generate S3 presigned PUT URL
            put_url = f"{settings.s3_endpoint_url}/{settings.s3_bucket_name}/{object_id}"
            
            media_objects.append(MediaObject(
                object_id=object_id,
                put_url=HttpRequest(
                    url=put_url,
                    headers={
                        "Content-Type": "application/octet-stream",
                        "x-amz-acl": "private"
                    }
                )
            ))
        
        return FlowStorage(media_objects=media_objects)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to allocate storage for flow {flow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Flow read-only endpoints
@router.head("/flows/{flow_id}/read_only")
async def head_flow_read_only(flow_id: str):
    """Return flow read_only path headers"""
    return {}

@router.get("/flows/{flow_id}/read_only", response_model=bool)
async def get_flow_read_only(
    flow_id: str,
    store: VASTStore = Depends(get_vast_store)
):
    """Returns the flow read_only property"""
    try:
        flow = await get_flow(store, flow_id)
        if not flow:
            raise HTTPException(status_code=404, detail="Flow not found")
        
        # Check if flow has read_only field, default to False
        if hasattr(flow, 'read_only'):
            return flow.read_only
        else:
            return False
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get flow read-only status for {flow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/flows/{flow_id}/read_only", status_code=204)
async def set_flow_read_only(
    flow_id: str,
    read_only: bool = Body(...),
    store: VASTStore = Depends(get_vast_store)
):
    """Set the read-only property"""
    try:
        flow = await get_flow(store, flow_id)
        if not flow:
            raise HTTPException(status_code=404, detail="Flow not found")
        
        # Update flow read_only status
        success = await store.update_flow_read_only(flow_id, read_only)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update flow read-only status")
        
        return  # 204 No Content
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to set flow read-only status for {flow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error") 