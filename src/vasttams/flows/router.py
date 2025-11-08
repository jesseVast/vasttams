"""
Minimal Flows Router

This is a minimal working flows router that can be imported without errors.
It provides basic endpoint structure that can be expanded later.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from typing import List, Optional
from .models import Flow
from ..common.filters import FlowFilters, FlowDetailFilters
from ..common.models import Tags, HttpRequest
from ..common.c2pa_utils import validate_c2pa_in_metadata  # C2PA support
from ..auth.rbac import require_admin, require_editor, require_viewer
from ..auth.middleware import UserSession
from ..service.storage_models import FlowStoragePost, FlowStorage, MediaObject
from ..common.responses import FlowsResponse
from ..common.storage.dependencies import get_storage_service
from ..common.storage.interfaces import StorageInterface
from ..core.config import get_settings
from ..events import EventManager
from ..core.dependencies import get_vast_db
from ..core.utils import log_pydantic_validation_error, safe_model_parse
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/flows", tags=["flows"])

# HEAD endpoints
@router.head("")
async def head_flows():
    """Return flows path headers"""
    return {}

@router.head("/{flow_id}")
async def head_flow(flow_id: str):
    """Return flow path headers"""
    return {}

# GET endpoints
@router.get("", response_model=FlowsResponse)
async def list_flows(
    source_id: Optional[str] = Query(None, description="Filter by source ID"),
    timerange: Optional[str] = Query(None, description="Filter by time range"),
    user_session: UserSession = Depends(require_viewer),
    format: Optional[str] = Query(None, description="Filter by format"),
    codec: Optional[str] = Query(None, description="Filter by codec"),
    label: Optional[str] = Query(None, description="Filter by label"),
    frame_width: Optional[int] = Query(None, description="Filter by frame width"),
    frame_height: Optional[int] = Query(None, description="Filter by frame height"),
    page: Optional[str] = Query(None, description="Pagination key"),
    limit: Optional[int] = Query(100, ge=1, le=1000, description="Number of results to return"),
    storage: StorageInterface = Depends(get_storage_service)
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
        flows = await storage.get_flows(filters)
        return FlowsResponse(data=flows)
    except Exception as e:
        logger.error("Failed to list flows: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{flow_id}", response_model=Flow)
async def get_flow_by_id(
    flow_id: str,
    include_timerange: bool = Query(False, description="Include timerange in response"),
    user_session: UserSession = Depends(require_viewer),
    timerange: Optional[str] = Query(None, description="Filter by time range"),
    storage: StorageInterface = Depends(get_storage_service)
):
    """Get a specific flow by ID"""
    try:
        filters = FlowDetailFilters(include_timerange=include_timerange, timerange=timerange)
        flow = await storage.get_flow(flow_id, filters)
        if not flow:
            raise HTTPException(status_code=404, detail="Flow not found")
        return flow
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get flow %s: %s", flow_id, e)
        raise HTTPException(status_code=500, detail="Internal server error")

# PUT endpoint
@router.put("/{flow_id}", response_model=Flow)
async def update_flow_by_id(
    flow_id: str,
    flow_data: dict,
    storage: StorageInterface = Depends(get_storage_service),
    user_session: UserSession = Depends(require_editor)
):
    """Update a flow"""
    try:
        # Get username for metadata
        username = user_session.username if user_session else "system"
        
        # Ensure the flow_id in the path matches the id in the request body
        flow_data["id"] = flow_id
        
        # Set updated_by from authenticated user (don't overwrite created_by)
        if "updated_by" not in flow_data or not flow_data.get("updated_by"):
            flow_data["updated_by"] = username
        
        # Create Flow object from the data based on format
        format_type = flow_data.get("format")
        
        if format_type == "urn:x-nmos:format:video":
            from .models import VideoFlow
            flow = VideoFlow(**flow_data)
        elif format_type == "urn:x-nmos:format:audio":
            from .models import AudioFlow
            flow = AudioFlow(**flow_data)
        elif format_type == "urn:x-tam:format:image":
            from .models import ImageFlow
            flow = ImageFlow(**flow_data)
        elif format_type == "urn:x-nmos:format:data":
            from .models import DataFlow
            flow = DataFlow(**flow_data)
        elif format_type == "urn:x-nmos:format:multi":
            from .models import MultiFlow
            flow = MultiFlow(**flow_data)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported flow format: {format_type}")
        
        success = await storage.update_flow(flow_id, flow)
        if not success:
            raise HTTPException(status_code=404, detail="Flow not found")
        
        # Get the updated flow for the event
        updated_flow = await storage.get_flow(flow_id)
        if not updated_flow:
            raise HTTPException(status_code=404, detail="Flow not found after update")
        
        # Emit flow updated event
        try:
            vast_db = get_vast_db()
            event_manager = EventManager(vast_db)
            await event_manager.emit_flow_event('flows/updated', updated_flow)
        except Exception as e:
            logger.warning("Failed to emit flow updated event: %s", e)
        
        return updated_flow
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update flow %s: %s", flow_id, e)
        raise HTTPException(status_code=500, detail="Internal server error")

# DELETE endpoint
@router.delete("/{flow_id}")
async def delete_flow_by_id(
    flow_id: str,
    user_session: UserSession = Depends(require_admin),
    cascade: bool = Query(True, description="Cascade delete related segments"),
    storage: StorageInterface = Depends(get_storage_service)
):
    """Delete a flow (hard delete only - TAMS compliant)"""
    try:
        # Get flow before deletion for event emission
        flow = await storage.get_flow(flow_id)
        
        success = await storage.delete_flow(flow_id, cascade)
        if not success:
            raise HTTPException(status_code=404, detail="Flow not found")
        
        # Emit flow deleted event
        if flow:
            try:
                vast_db = get_vast_db()
                event_manager = EventManager(vast_db)
                await event_manager.emit_flow_event('flows/deleted', flow)
            except Exception as e:
                logger.warning("Failed to emit flow deleted event: %s", e)
        
        return {"message": "Flow hard deleted successfully"}
        
    except ValueError as e:
        # Handle dependency violations with 409 Conflict
        logger.warning("Dependency violation deleting flow %s: %s", flow_id, e)
        raise HTTPException(status_code=409, detail=str(e))
    except HTTPException:
        # Re-raise HTTP exceptions (including 409 Conflict from constraint violations)
        raise
    except Exception as e:
        logger.error("Failed to delete flow %s: %s", flow_id, e)
        raise HTTPException(status_code=500, detail="Internal server error")

# POST endpoint
@router.post("", response_model=Flow, status_code=201)
async def create_new_flow(
    flow: Flow,
    storage: StorageInterface = Depends(get_storage_service),
    user_session: UserSession = Depends(require_editor)
):
    """Create a new flow"""
    try:
        # Get username for metadata
        username = user_session.username if user_session else "system"
        
        # Set created_by and updated_by from authenticated user
        if not flow.created_by:
            flow.created_by = username
        if not flow.updated_by:
            flow.updated_by = username
        
        # Validate C2PA provenance if present in tags
        if flow.tags and flow.tags.root:
            tags_dict = flow.tags.root
            c2pa_is_valid = validate_c2pa_in_metadata(tags_dict)
            if not c2pa_is_valid:
                logger.warning("Flow %s has invalid C2PA metadata in tags", flow.id)
        
        success = await storage.create_flow(flow)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to create flow")
        
        # Emit flow created event
        try:
            vast_db = get_vast_db()
            event_manager = EventManager(vast_db)
            await event_manager.emit_flow_event('flows/created', flow)
        except Exception as e:
            logger.warning("Failed to emit flow created event: %s", e)
        
        return flow
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to create flow: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")

# Individual field endpoints - minimal implementation
@router.head("/{flow_id}/tags")
async def head_flow_tags(flow_id: str):
    """Return flow tags path headers"""
    return {}

@router.get("/{flow_id}/tags")
async def get_flow_tags(
    flow_id: str,
    storage: StorageInterface = Depends(get_storage_service)
):
    """Get flow tags"""
    try:
        flow = await storage.get_flow(flow_id)
        if not flow:
            raise HTTPException(status_code=404, detail="Flow not found")
        return flow.tags or {}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get flow tags for %s: %s", flow_id, e)
        raise HTTPException(status_code=500, detail="Internal server error")

# Individual flow tag endpoints
@router.head("/{flow_id}/tags/{name}")
async def head_flow_tag(flow_id: str, name: str):
    """Return flow tag path headers"""
    return {}

@router.get("/{flow_id}/tags/{name}", response_model=str)
async def get_flow_tag(
    flow_id: str,
    name: str,
    storage: StorageInterface = Depends(get_storage_service)
):
    """Get flow tag value"""
    try:
        tags = await storage.get_flow_tags(flow_id)
        logger.debug("Retrieved tags for flow %s: %s", flow_id, tags)
        logger.debug("Tags type: %s, tags.root: %s", type(tags), tags.root if tags else "None")
        logger.debug("Looking for tag name: %s", name)
        
        if not tags or name not in tags:
            logger.debug("Tag %s not found in tags: %s", name, tags.root if tags else "None")
            raise HTTPException(status_code=404, detail="Tag not found")
        
        return tags[name]
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get flow tag %s for %s: %s", name, flow_id, e)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/{flow_id}/tags/{name}", status_code=204)
async def update_flow_tag(
    flow_id: str,
    name: str,
    value: str = Body(..., media_type="text/plain"),
    storage: StorageInterface = Depends(get_storage_service)
):
    """Update flow tag value"""
    try:
        success = await storage.update_flow_tag(flow_id, name, value)
        if not success:
            raise HTTPException(status_code=404, detail="Flow not found")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update flow tag %s for %s: %s", name, flow_id, e)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/{flow_id}/tags/{name}", status_code=204)
async def delete_flow_tag(
    flow_id: str,
    name: str,
    storage: StorageInterface = Depends(get_storage_service)
):
    """Delete flow tag"""
    try:
        success = await storage.delete_flow_tag(flow_id, name)
        if not success:
            raise HTTPException(status_code=404, detail="Flow or tag not found")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete flow tag %s for %s: %s", name, flow_id, e)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.head("/{flow_id}/description")
async def head_flow_description(flow_id: str):
    """Return flow description path headers"""
    return {}

@router.get("/{flow_id}/description")
async def get_flow_description(
    flow_id: str,
    storage: StorageInterface = Depends(get_storage_service)
):
    """Get flow description"""
    try:
        flow = await storage.get_flow(flow_id)
        if not flow:
            raise HTTPException(status_code=404, detail="Flow not found")
        return flow.description or ""
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get flow description for %s: %s", flow_id, e)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/{flow_id}/description", status_code=204)
async def update_flow_description(
    flow_id: str,
    description: str = Body(..., media_type="text/plain"),
    storage: StorageInterface = Depends(get_storage_service)
):
    """Update flow description"""
    try:
        success = await storage.update_flow_description(flow_id, description)
        if not success:
            raise HTTPException(status_code=404, detail="Flow not found")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update flow description for %s: %s", flow_id, e)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/{flow_id}/description", status_code=204)
async def delete_flow_description(
    flow_id: str,
    storage: StorageInterface = Depends(get_storage_service)
):
    """Delete flow description"""
    try:
        success = await storage.delete_flow_description(flow_id)
        if not success:
            raise HTTPException(status_code=404, detail="Flow not found")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete flow description for %s: %s", flow_id, e)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.head("/{flow_id}/label")
async def head_flow_label(flow_id: str):
    """Return flow label path headers"""
    return {}

@router.get("/{flow_id}/label")
async def get_flow_label(
    flow_id: str,
    storage: StorageInterface = Depends(get_storage_service)
):
    """Get flow label"""
    try:
        flow = await storage.get_flow(flow_id)
        if not flow:
            raise HTTPException(status_code=404, detail="Flow not found")
        return flow.label or ""
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get flow label for %s: %s", flow_id, e)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/{flow_id}/label", status_code=204)
async def update_flow_label(
    flow_id: str,
    label: str = Body(..., media_type="text/plain"),
    storage: StorageInterface = Depends(get_storage_service)
):
    """Update flow label"""
    try:
        success = await storage.update_flow_label(flow_id, label)
        if not success:
            raise HTTPException(status_code=404, detail="Flow not found")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update flow label for %s: %s", flow_id, e)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/{flow_id}/label", status_code=204)
async def delete_flow_label(
    flow_id: str,
    storage: StorageInterface = Depends(get_storage_service)
):
    """Delete flow label"""
    try:
        success = await storage.delete_flow_label(flow_id)
        if not success:
            raise HTTPException(status_code=404, detail="Flow not found")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete flow label for %s: %s", flow_id, e)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.head("/{flow_id}/read_only")
async def head_flow_read_only(flow_id: str):
    """Return flow read-only path headers"""
    return {}

# Flow collection endpoints
@router.head("/{flow_id}/flow_collection")
async def head_flow_collection(flow_id: str):
    """Return flow collection path headers"""
    return {}

@router.get("/{flow_id}/flow_collection")
async def get_flow_collection(
    flow_id: str,
    storage: StorageInterface = Depends(get_storage_service)
):
    """Get flow collection"""
    try:
        flow = await storage.get_flow(flow_id)
        if not flow:
            raise HTTPException(status_code=404, detail="Flow not found")
        # Return collection data if available
        if flow.flow_collection is not None:
            # FlowCollection is a RootModel, so we need to get the root value
            if hasattr(flow.flow_collection, 'root'):
                return flow.flow_collection.root
            else:
                return flow.flow_collection
        return []
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get flow collection for %s: %s", flow_id, e)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/{flow_id}/flow_collection", status_code=201)
async def update_flow_collection(
    flow_id: str,
    collection_data: List[dict] = Body(...),  # Accept list of FlowCollectionItem dicts
    storage: StorageInterface = Depends(get_storage_service)
):
    """Update flow collection
    
    collection_data should be a list of FlowCollectionItem objects:
    [
        {"id": "flow-uuid", "role": "video"},
        {"id": "flow-uuid", "role": "audio"}
    ]
    """
    try:
        from ..common.models import FlowCollection
        import json
        # Validate the collection data
        collection = FlowCollection.model_validate(collection_data)
        
        # Get the existing flow to verify it exists
        flow = await storage.get_flow(flow_id)
        if not flow:
            raise HTTPException(status_code=404, detail="Flow not found")
        
        # Update flow_collection directly in the database
        # Convert collection to JSON string for storage
        collection_json = json.dumps(collection.model_dump())
        
        # Update flow_collection field directly in database
        vast_db = get_vast_db()
        flows_table = vast_db.get_qualified_table_name("flows")
        
        # Escape single quotes in JSON
        escaped_json = collection_json.replace("'", "''")
        sql = f"UPDATE {flows_table} SET flow_collection = '{escaped_json}' WHERE id = '{flow_id}'"
        vast_db.execute_sql(sql)
        
        return {"message": "Flow collection updated successfully", "collection": collection.model_dump()}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update flow collection for %s: %s", flow_id, e)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/{flow_id}/flow_collection", status_code=204)
async def delete_flow_collection(
    flow_id: str,
    storage: StorageInterface = Depends(get_storage_service)
):
    """Delete flow collection"""
    try:
        # For now, just return success - collection management not fully implemented
        return
    except Exception as e:
        logger.error("Failed to delete flow collection for %s: %s", flow_id, e)
        raise HTTPException(status_code=500, detail="Internal server error")

# Flow bit rate endpoints
@router.head("/{flow_id}/max_bit_rate")
async def head_flow_max_bit_rate(flow_id: str):
    """Return flow max bit rate path headers"""
    return {}

@router.get("/{flow_id}/max_bit_rate")
async def get_flow_max_bit_rate(
    flow_id: str,
    storage: StorageInterface = Depends(get_storage_service)
):
    """Get flow max bit rate"""
    try:
        flow = await storage.get_flow(flow_id)
        if not flow:
            raise HTTPException(status_code=404, detail="Flow not found")
        return getattr(flow, 'max_bit_rate', None) or ""
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get flow max bit rate for %s: %s", flow_id, e)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/{flow_id}/max_bit_rate", status_code=201)
async def update_flow_max_bit_rate(
    flow_id: str,
    bit_rate: str = Body(..., media_type="text/plain"),
    storage: StorageInterface = Depends(get_storage_service)
):
    """Update flow max bit rate"""
    try:
        # For now, just return success - bit rate management not fully implemented
        return
    except Exception as e:
        logger.error("Failed to update flow max bit rate for %s: %s", flow_id, e)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/{flow_id}/max_bit_rate", status_code=204)
async def delete_flow_max_bit_rate(
    flow_id: str,
    storage: StorageInterface = Depends(get_storage_service)
):
    """Delete flow max bit rate"""
    try:
        # For now, just return success - bit rate management not fully implemented
        return
    except Exception as e:
        logger.error("Failed to delete flow max bit rate for %s: %s", flow_id, e)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.head("/{flow_id}/avg_bit_rate")
async def head_flow_avg_bit_rate(flow_id: str):
    """Return flow avg bit rate path headers"""
    return {}

@router.get("/{flow_id}/avg_bit_rate")
async def get_flow_avg_bit_rate(
    flow_id: str,
    storage: StorageInterface = Depends(get_storage_service)
):
    """Get flow avg bit rate"""
    try:
        flow = await storage.get_flow(flow_id)
        if not flow:
            raise HTTPException(status_code=404, detail="Flow not found")
        return getattr(flow, 'avg_bit_rate', None) or ""
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get flow avg bit rate for %s: %s", flow_id, e)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/{flow_id}/avg_bit_rate", status_code=201)
async def update_flow_avg_bit_rate(
    flow_id: str,
    bit_rate: str = Body(..., media_type="text/plain"),
    storage: StorageInterface = Depends(get_storage_service)
):
    """Update flow avg bit rate"""
    try:
        # For now, just return success - bit rate management not fully implemented
        return
    except Exception as e:
        logger.error("Failed to update flow avg bit rate for %s: %s", flow_id, e)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/{flow_id}/avg_bit_rate", status_code=204)
async def delete_flow_avg_bit_rate(
    flow_id: str,
    storage: StorageInterface = Depends(get_storage_service)
):
    """Delete flow avg bit rate"""
    try:
        # For now, just return success - bit rate management not fully implemented
        return
    except Exception as e:
        logger.error("Failed to delete flow avg bit rate for %s: %s", flow_id, e)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/{flow_id}/recalculate-bit-rates", status_code=200)
async def recalculate_flow_bit_rates(
    flow_id: str,
    storage: StorageInterface = Depends(get_storage_service)
):
    """Manually recalculate and update bit rates for a flow from its segments"""
    try:
        # Verify flow exists
        flow = await storage.get_flow(flow_id)
        if not flow:
            raise HTTPException(status_code=404, detail="Flow not found")
        
        # Calculate bit rates
        from ..flows.service import FlowStorageService
        from ..core.dependencies import get_s3_client
        s3_client = get_s3_client()
        vast_db = get_vast_db()
        
        flow_service = FlowStorageService(vast_db, s3_client)
        await flow_service._calculate_and_update_bit_rates(flow_id)
        
        # Return updated flow
        updated_flow = await storage.get_flow(flow_id)
        return {
            "flow_id": flow_id,
            "avg_bit_rate": updated_flow.avg_bit_rate,
            "max_bit_rate": updated_flow.max_bit_rate,
            "message": "Bit rates recalculated successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to recalculate bit rates for flow %s: %s", flow_id, e)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{flow_id}/read_only")
async def get_flow_read_only(
    flow_id: str,
    storage: StorageInterface = Depends(get_storage_service)
):
    """Get flow read-only status"""
    try:
        flow = await storage.get_flow(flow_id)
        if not flow:
            raise HTTPException(status_code=404, detail="Flow not found")
        return flow.read_only or False
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get flow read-only status for %s: %s", flow_id, e)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/{flow_id}/read_only", status_code=204)
async def update_flow_read_only(
    flow_id: str,
    read_only: bool = Body(..., media_type="application/json"),
    storage: StorageInterface = Depends(get_storage_service)
):
    """Update flow read-only status"""
    try:
        success = await storage.update_flow_read_only(flow_id, read_only)
        if not success:
            raise HTTPException(status_code=404, detail="Flow not found")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update flow read-only status for %s: %s", flow_id, e)
        raise HTTPException(status_code=500, detail="Internal server error")
