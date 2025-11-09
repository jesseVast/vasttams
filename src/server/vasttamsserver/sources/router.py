from fastapi import APIRouter, Depends, HTTPException, Query, Body, Request
from typing import List, Optional
import uuid
from pydantic import ValidationError
from .models import Source
from ..common.filters import SourceFilters
from ..common.responses import SourcesResponse
from ..common.models import Tags
from ..common.c2pa_utils import validate_c2pa_in_metadata  # C2PA support
from ..common.storage import get_storage_service
from ..common.storage.interfaces import StorageInterface
from ..events import EventManager
from ..core.dependencies import get_vast_db
from ..core.utils import log_pydantic_validation_error, safe_model_parse, parse_query_filters
from ..auth.rbac import require_admin, require_editor, require_viewer
from ..auth.middleware import UserSession
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
    request: Request,
    label: Optional[str] = Query(None, description="Filter by label"),
    format: Optional[str] = Query(None, description="Filter by format"),
    page: Optional[str] = Query(None, description="Pagination key"),
    limit: Optional[int] = Query(100, ge=1, le=1000, description="Number of results to return"),
    storage: StorageInterface = Depends(get_storage_service),
    user_session: UserSession = Depends(require_viewer)
):
    """List sources with optional filtering (TAMS 8.0 with tag filtering)
    
    Note: source_collection is not included in list responses for performance.
    Use GET /sources/{source_id} to retrieve a single source with source_collection computed on-demand.
    """
    try:
        # Extract all query parameters for tag filtering
        query_params = dict(request.query_params)
        parsed_filters = parse_query_filters(query_params)
        
        # Build SourceFilters with tag filtering support
        filters = SourceFilters(
            label=label or parsed_filters.get("label"),
            format=format or parsed_filters.get("format"),
            page=page or parsed_filters.get("page"),
            limit=limit or parsed_filters.get("limit"),
            tag_filters=parsed_filters.get("tag_filters", {}),
            tag_exists_filters=parsed_filters.get("tag_exists_filters", {})
        )
        sources = await storage.get_sources(filters)
        return SourcesResponse(data=sources)
    except Exception as e:
        logger.error("Failed to list sources: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{source_id}", response_model=Source)
async def get_source_by_id(
    source_id: str,
    storage: StorageInterface = Depends(get_storage_service),
    user_session: UserSession = Depends(require_viewer)
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
    storage: StorageInterface = Depends(get_storage_service),
    user_session: UserSession = Depends(require_editor)
):
    """Create a new source"""
    try:
        # Get username for logging and metadata
        username = user_session.username if user_session else "system"
        
        # Set created_by and updated_by from authenticated user
        if not source.created_by:
            source.created_by = username
        if not source.updated_by:
            source.updated_by = username
        
        # Log successful validation with user context
        logger.debug("User %s creating source with ID: %s, format: %s", username, source.id, source.format)
        
        # Validate C2PA provenance if present in tags
        if source.tags and source.tags.root:
            tags_dict = source.tags.root
            c2pa_is_valid = validate_c2pa_in_metadata(tags_dict)
            if not c2pa_is_valid:
                logger.warning("User %s: Source %s has invalid C2PA metadata in tags", username, source.id)
        
        success = await storage.create_source(source)
        if not success:
            logger.error("User %s: Storage layer failed to create source %s", username, source.id)
            raise HTTPException(status_code=500, detail="Failed to create source")
        
        # Emit source created event
        try:
            vast_db = get_vast_db()
            event_manager = EventManager(vast_db)
            await event_manager.emit_source_event('sources/created', source)
        except Exception as e:
            logger.warning("User %s: Failed to emit source created event: %s", username, e)
        
        logger.debug("User %s successfully created source: %s", username, source.id)
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
        
        # Check for duplicate IDs in the batch
        source_ids = [source.id for source in sources]
        if len(source_ids) != len(set(source_ids)):
            duplicate_ids = [sid for sid in source_ids if source_ids.count(sid) > 1]
            raise HTTPException(status_code=409, detail=f"Duplicate source IDs in batch: {list(set(duplicate_ids))}")
        
        # Create sources one by one using the storage service
        created_sources = []
        for source in sources:
            # Check if source already exists
            existing = await storage.get_source(source.id)
            if existing:
                raise HTTPException(status_code=409, detail=f"Source {source.id} already exists")
            
            success = await storage.create_source(source)
            if not success:
                raise HTTPException(status_code=500, detail=f"Failed to create source {source.id}")
            created_sources.append(source)
        
        logger.debug("Successfully created %d sources", len(created_sources))
        
        # Emit source created events for batch creation
        try:
            vast_db = get_vast_db()
            event_manager = EventManager(vast_db)
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
    storage: StorageInterface = Depends(get_storage_service),
    user_session: UserSession = Depends(require_admin)
):
    """Delete a source (hard delete only - TAMS compliant)"""
    try:
        # Validate UUID format
        from ..common.models import validate_tams_uuid
        try:
            validate_tams_uuid(source_id)
        except ValueError as e:
            raise HTTPException(status_code=422, detail=f"Invalid source ID format: {str(e)}")
        
        # Log the cascade parameter for debugging
        logger.debug("Deleting source %s with cascade=%s", source_id, cascade)
        
        # Get source before deletion for event emission
        source = await storage.get_source(source_id)
        
        success = await storage.delete_source(source_id, cascade)
        if not success:
            raise HTTPException(status_code=404, detail="Source not found")
        
        # Emit source deleted event
        if source:
            try:
                vast_db = get_vast_db()
                event_manager = EventManager(vast_db)
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
    request: Request,
    storage: StorageInterface = Depends(get_storage_service),
    user_session: UserSession = Depends(require_editor)
):
    """Update Source Tag Value (supports both string and JSON array values)"""
    try:
        # Read body to support both text/plain and application/json
        body = await request.body()
        content_type = request.headers.get("content-type", "").lower()
        
        # Parse value based on content type
        if "application/json" in content_type:
            # JSON array value
            import json
            try:
                value = json.loads(body.decode('utf-8'))
                # If it's a list, convert to JSON string for storage
                if isinstance(value, list):
                    value = json.dumps(value)
                else:
                    value = str(value)
            except (json.JSONDecodeError, ValueError):
                # Fallback to string if JSON parsing fails
                value = body.decode('utf-8')
        else:
            # Text/plain string value
            value = body.decode('utf-8')
        
        source = await storage.get_source(source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        
        # Update specific tag using storage service
        logger.debug("Source tag update - source_id: %s, name: %s, value: %s", source_id, name, value)
        logger.debug("Value type: %s", type(value))
        
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
    storage: StorageInterface = Depends(get_storage_service),
    user_session: UserSession = Depends(require_editor)
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
    request: Request,
    storage: StorageInterface = Depends(get_storage_service),
    user_session: UserSession = Depends(require_editor),
    description: Optional[str] = Query(None, description="Description value (alternative to request body)")
):
    """Update source description"""
    try:
        # Read text/plain body first, fallback to query parameter
        # Also check query params directly from request in case Query() doesn't work
        body_description = await request.body()
        body_description = body_description.decode('utf-8').strip() if body_description else ""
        
        # Also check query params directly from request
        query_description = request.query_params.get('description')
        if query_description:
            query_description = query_description.strip()
        
        # Use body if present and non-empty, otherwise use query parameter
        if body_description:
            description_value = body_description
            logger.debug("Using description from request body: %s", description_value)
        elif description is not None and isinstance(description, str) and description.strip():
            # Use query parameter from FastAPI Query dependency
            description_value = description.strip()
            logger.debug("Using description from FastAPI Query parameter: %s", description_value)
        elif query_description:
            # Fallback: use query parameter from request directly
            description_value = query_description
            logger.debug("Using description from request.query_params: %s", description_value)
        else:
            # Neither body nor query parameter provided - allow empty description
            description_value = ""
        
        # Get username for metadata
        username = user_session.username if user_session else "system"
        
        source = await storage.get_source(source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        
        source.description = description_value
        source.updated_by = username
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
    storage: StorageInterface = Depends(get_storage_service),
    user_session: UserSession = Depends(require_editor)
):
    """Delete source description"""
    try:
        source = await storage.get_source(source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        
        # Get username for metadata
        username = user_session.username if user_session else "system"
        
        source.description = None
        source.updated_by = username
        
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
    request: Request,
    storage: StorageInterface = Depends(get_storage_service),
    user_session: UserSession = Depends(require_editor)
):
    """Update source label"""
    try:
        # Check query params first (before reading body, as body reading might affect query param access)
        query_label = request.query_params.get('label')
        
        # Read text/plain body
        body_label = await request.body()
        body_label = body_label.decode('utf-8').strip() if body_label else ""
        
        # Use body if present and non-empty, otherwise use query parameter
        # Priority: body > request.query_params
        if body_label:
            label_value = body_label
        elif query_label:
            # Use query parameter from request directly
            label_value = query_label.strip() if query_label else ""
        else:
            # Neither body nor query parameter provided
            logger.error("No label provided! body='%s', query_label='%s', all_params=%s, url=%s", 
                         body_label, query_label, dict(request.query_params), str(request.url))
            raise HTTPException(status_code=400, detail="Label value required in request body or query parameter")
        
        # Get username for metadata
        username = user_session.username if user_session else "system"
        
        source = await storage.get_source(source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        
        # Store original label for debugging
        original_label = source.label
        
        source.label = label_value
        source.updated_by = username
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
    storage: StorageInterface = Depends(get_storage_service),
    user_session: UserSession = Depends(require_editor)
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
