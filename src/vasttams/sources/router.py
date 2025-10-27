from fastapi import APIRouter, Depends, HTTPException, Query, Body
from typing import List, Optional
import uuid
from pydantic import ValidationError
from .models import Source
from ..common.filters import SourceFilters
from ..common.responses import SourcesResponse
from ..common.models import Tags
from ..common.storage import get_storage_service
from ..common.storage.interfaces import StorageInterface
from ..core.event_manager import EventManager
from ..core.utils import log_pydantic_validation_error, safe_model_parse
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sources", tags=["sources"])

# HEAD endpoints
@router.head("")
async def head_sources():
    """Return sources path headers"""
    return {}



@router.options("")
async def options_sources():
    """Sources endpoint OPTIONS method for CORS preflight"""
    return {}

@router.head("/{source_id}")
async def head_source(source_id: str):
    """Return source path headers"""
    return {}

# GET endpoints
@router.get("", response_model=SourcesResponse)
async def list_sources(
    label: Optional[str] = Query(None, description="Filter by label"),
    format: Optional[str] = Query(None, description="Filter by format"),
    page: Optional[str] = Query(None, description="Pagination key"),
    limit: Optional[int] = Query(100, ge=1, le=1000, description="Number of results to return"),
    storage: StorageInterface = Depends(get_storage_service)
):
    """List sources with optional filtering"""
    try:
        filters = SourceFilters(label=label, format=format, page=page, limit=limit)
        sources = await storage.get_sources(filters)
        return SourcesResponse(data=sources)
    except Exception as e:
        logger.error("Failed to list sources: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{source_id}", response_model=Source)
async def get_source_by_id(
    source_id: str,
    storage: StorageInterface = Depends(get_storage_service)
):
    """Get a specific source by ID"""
    try:
        source = await storage.get_source(source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        return source
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get source %s: %s", source_id, e)
        raise HTTPException(status_code=500, detail="Internal server error")

# POST endpoint
@router.post("", response_model=Source, status_code=201)
async def create_new_source(
    source: Source,
    storage: StorageInterface = Depends(get_storage_service)
):
    """Create a new source"""
    try:
        # Log successful validation
        logger.info("Creating source with ID: %s, format: %s", source.id, source.format)
        
        success = await storage.create_source(source)
        if not success:
            logger.error("Storage layer failed to create source %s", source.id)
            raise HTTPException(status_code=500, detail="Failed to create source")
        
        # Emit source created event
        try:
            event_manager = EventManager(storage)
            await event_manager.emit_source_event('sources/created', source)
        except Exception as e:
            logger.warning("Failed to emit source created event: %s", e)
        
        logger.info("Successfully created source: %s", source.id)
        return source
    except ValidationError as e:
        # This shouldn't happen as FastAPI handles validation before the function,
        # but we'll catch it for completeness
        error_msg = log_pydantic_validation_error(
            error=e,
            context="POST /sources",
            input_data=None,  # FastAPI already parsed it
            model_name="Source"
        )
        raise HTTPException(status_code=422, detail=error_msg)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to create source: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")

# Batch POST endpoint
@router.post("/batch", response_model=List[Source], status_code=201)
async def create_sources_batch(
    sources: List[Source],
    storage: StorageInterface = Depends(get_storage_service)
):
    """Create multiple sources using conditional logic: single insert for 1 source, batch insert for multiple"""
    try:
        if not sources:
            raise HTTPException(status_code=400, detail="No sources provided")
        
        # Create sources one by one using the storage service
        created_sources = []
        for source in sources:
            success = await storage.create_source(source)
            if not success:
                raise HTTPException(status_code=500, detail=f"Failed to create source {source.id}")
            created_sources.append(source)
        
        logger.info("Successfully created %d sources", len(created_sources))
        
        # Emit source created events for batch creation
        try:
            event_manager = EventManager(storage)
            for source in created_sources:
                await event_manager.emit_source_event('sources/created', source)
        except Exception as e:
            logger.warning("Failed to emit batch source created events: %s", e)
        
        return created_sources
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to create sources batch: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")


# DELETE endpoint
@router.delete("/{source_id}")
async def delete_source_by_id(
    source_id: str,
    cascade: bool = Query(True, description="Cascade delete related flows"),
    storage: StorageInterface = Depends(get_storage_service)
):
    """Delete a source (hard delete only - TAMS compliant)"""
    try:
        # Log the cascade parameter for debugging
        logger.info("Deleting source %s with cascade=%s", source_id, cascade)
        
        # Get source before deletion for event emission
        source = await storage.get_source(source_id)
        
        success = await storage.delete_source(source_id, cascade)
        if not success:
            raise HTTPException(status_code=404, detail="Source not found")
        
        # Emit source deleted event
        if source:
            try:
                event_manager = EventManager(storage)
                await event_manager.emit_source_event('sources/deleted', source)
            except Exception as e:
                logger.warning("Failed to emit source deleted event: %s", e)
        
        return {"message": "Source hard deleted successfully"}
        
    except ValueError as e:
        # ✅ NEW: Handle dependency violations with 409 Conflict
        logger.warning("Dependency violation deleting source %s: %s", source_id, e)
        raise HTTPException(status_code=409, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete source %s: %s", source_id, e)
        raise HTTPException(status_code=500, detail="Internal server error")



# Source tags endpoints
@router.head("/{source_id}/tags")
async def head_source_tags(source_id: str):
    """Return Source tags path headers"""
    return {}

@router.get("/{source_id}/tags", response_model=Tags)
async def list_source_tags(
    source_id: str,
    storage: StorageInterface = Depends(get_storage_service)
):
    """List Source Tags"""
    try:
        source = await storage.get_source(source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        
        # Get tags from the storage service
        tags = await storage.get_source_tags(source_id)
        return tags if tags else Tags({})
        
    except ValidationError as e:
        error_msg = log_pydantic_validation_error(
            error=e,
            context=f"GET /{source_id}/tags",
            input_data={"source_id": source_id, "source": str(source) if source else "None"},
            model_name="Tags"
        )
        raise HTTPException(status_code=422, detail=error_msg)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to list source tags for %s: %s", source_id, e)
        raise HTTPException(status_code=500, detail="Internal server error")

# TAMS API does not support bulk tags update - only individual tag operations
# This endpoint removed for TAMS compliance
# Code preserved in VASTStore.update_source_tags() for potential future use

@router.head("/{source_id}/tags/{name}")
async def head_source_tag(source_id: str, name: str):
    """Return Source tag path headers"""
    return {}

@router.get("/{source_id}/tags/{name}", response_model=str)
async def get_source_tag(
    source_id: str,
    name: str,
    storage: StorageInterface = Depends(get_storage_service)
):
    """Source Tag Value"""
    try:
        source = await storage.get_source(source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        
        # Get specific tag value from the storage service
        tag_value = await storage.get_source_tag(source_id, name)
        if tag_value is not None:
            return tag_value
        else:
            raise HTTPException(status_code=404, detail="Tag not found")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get source tag %s for %s: %s", name, source_id, e)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/{source_id}/tags/{name}", status_code=204)
async def update_source_tag(
    source_id: str,
    name: str,
    value: str = Body(..., media_type="text/plain"),
    storage: StorageInterface = Depends(get_storage_service)
):
    """Update Source Tag Value"""
    try:
        source = await storage.get_source(source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        
        # Update specific tag using storage service
        logger.info("🔍 DEBUG: Source tag update - source_id: %s, name: %s, value: %s", source_id, name, value)
        logger.info("🔍 DEBUG: Value type: %s", type(value))
        
        success = await storage.update_source_tag(source_id, name, value)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update source tag")
        
        # Emit source updated event
        try:
            event_manager = EventManager(storage)
            await event_manager.emit_source_event('sources/updated', source)
        except Exception as e:
            logger.warning("Failed to emit source updated event: %s", e)
        
        return  # 204 No Content
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update source tag %s for %s: %s", name, source_id, e)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/{source_id}/tags/{name}", status_code=204)
async def delete_source_tag(
    source_id: str,
    name: str,
    storage: StorageInterface = Depends(get_storage_service)
):
    """Delete Source Tag"""
    try:
        source = await storage.get_source(source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        
        # Remove specific tag using storage service
        success = await storage.delete_source_tag(source_id, name)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete source tag")
        
        # Emit source updated event
        try:
            event_manager = EventManager(storage)
            await event_manager.emit_source_event('sources/updated', source)
        except Exception as e:
            logger.warning("Failed to emit source updated event: %s", e)
        
        return  # 204 No Content
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete source tag %s for %s: %s", name, source_id, e)
        raise HTTPException(status_code=500, detail="Internal server error")



@router.head("/{source_id}/description")
async def head_source_description(source_id: str):
    """Return source description path headers"""
    return {}

@router.get("/{source_id}/description")
async def get_source_description(
    source_id: str,
    storage: StorageInterface = Depends(get_storage_service)
):
    """Get source description"""
    try:
        source = await storage.get_source(source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        return source.description or ""
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get source description for %s: %s", source_id, e)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/{source_id}/description")
async def update_source_description(
    source_id: str,
    description: str,
    storage: StorageInterface = Depends(get_storage_service)
):
    """Update source description"""
    try:
        source = await storage.get_source(source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        
        source.description = description
        success = await storage.update_source(source_id, source)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update source description")
        
        # Emit source updated event
        try:
            event_manager = EventManager(storage)
            await event_manager.emit_source_event('sources/updated', source)
        except Exception as e:
            logger.warning("Failed to emit source updated event: %s", e)
        
        return {"message": "Description updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update source description for %s: %s", source_id, e)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/{source_id}/description")
async def delete_source_description(
    source_id: str,
    storage: StorageInterface = Depends(get_storage_service)
):
    """Delete source description"""
    try:
        source = await storage.get_source(source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        
        source.description = None
        
        # Save the updated source
        success = await storage.update_source(source_id, source)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete source description")
        
        # Emit source updated event
        try:
            event_manager = EventManager(storage)
            await event_manager.emit_source_event('sources/updated', source)
        except Exception as e:
            logger.warning("Failed to emit source updated event: %s", e)
        
        return {"message": "Description deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete source description for %s: %s", source_id, e)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.head("/{source_id}/label")
async def head_source_label(source_id: str):
    """Return source label path headers"""
    return {}

@router.get("/{source_id}/label")
async def get_source_label(
    source_id: str,
    storage: StorageInterface = Depends(get_storage_service)
):
    """Get source label"""
    try:
        source = await storage.get_source(source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        return source.label or ""
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get source label for %s: %s", source_id, e)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/{source_id}/label")
async def update_source_label(
    source_id: str,
    label: str,
    storage: StorageInterface = Depends(get_storage_service)
):
    """Update source label"""
    try:
        source = await storage.get_source(source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        
        source.label = label
        success = await storage.update_source(source_id, source)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update source label")
        
        # Emit source updated event
        try:
            event_manager = EventManager(storage)
            await event_manager.emit_source_event('sources/updated', source)
        except Exception as e:
            logger.warning("Failed to emit source updated event: %s", e)
        
        return {"message": "Label updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update source label for %s: %s", source_id, e)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/{source_id}/label")
async def delete_source_label(
    source_id: str,
    storage: StorageInterface = Depends(get_storage_service)
):
    """Delete source label"""
    try:
        source = await storage.get_source(source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        
        source.label = None
        
        # Save the updated source
        success = await storage.update_source(source_id, source)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete source label")
        
        # Emit source updated event
        try:
            event_manager = EventManager(storage)
            await event_manager.emit_source_event('sources/updated', source)
        except Exception as e:
            logger.warning("Failed to emit source updated event: %s", e)
        
        return {"message": "Label deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete source label for %s: %s", source_id, e)
        raise HTTPException(status_code=500, detail="Internal server error")
