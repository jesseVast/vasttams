from fastapi import APIRouter, Depends, HTTPException, Query, Body
from typing import List, Optional
from ..models.models import Source, SourcesResponse, SourceFilters, Tags
from .sources import get_sources, get_source, create_source, delete_source
from ..storage.vast_store import VASTStore
from ..core.dependencies import get_vast_store
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# HEAD endpoints
@router.head("/sources")
async def head_sources():
    """Return sources path headers"""
    return {}

@router.options("/sources")
async def options_sources():
    """Sources endpoint OPTIONS method for CORS preflight"""
    return {}

@router.head("/sources/{source_id}")
async def head_source(source_id: str):
    """Return source path headers"""
    return {}

# GET endpoints
@router.get("/sources", response_model=SourcesResponse)
async def list_sources(
    label: Optional[str] = Query(None, description="Filter by label"),
    format: Optional[str] = Query(None, description="Filter by format"),
    page: Optional[str] = Query(None, description="Pagination key"),
    limit: Optional[int] = Query(100, ge=1, le=1000, description="Number of results to return"),
    store: VASTStore = Depends(get_vast_store)
):
    """List sources with optional filtering"""
    try:
        filters = SourceFilters(label=label, format=format, page=page, limit=limit)
        sources = await get_sources(store, filters)
        return SourcesResponse(data=sources)
    except Exception as e:
        logger.error(f"Failed to list sources: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/sources/{source_id}", response_model=Source)
async def get_source_by_id(
    source_id: str,
    store: VASTStore = Depends(get_vast_store)
):
    """Get a specific source by ID"""
    try:
        source = await get_source(store, source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        return source
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get source {source_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# POST endpoint
@router.post("/sources", response_model=Source, status_code=201)
async def create_new_source(
    source: Source,
    store: VASTStore = Depends(get_vast_store)
):
    """Create a new source"""
    try:
        success = await create_source(store, source)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to create source")
        return source
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create source: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Batch POST endpoint
@router.post("/sources/batch", response_model=List[Source], status_code=201)
async def create_sources_batch(
    sources: List[Source],
    store: VASTStore = Depends(get_vast_store)
):
    """Create multiple sources in a single batch operation using VAST's native batch insert"""
    try:
        # Convert Pydantic models to the format expected by insert_batch_efficient
        # The method expects Dict[str, List[Any]] where keys are column names
        if not sources:
            raise HTTPException(status_code=400, detail="No sources provided")
        
        # Get the first source to determine column names
        first_source = sources[0].model_dump()
        column_names = list(first_source.keys())
        
        # Transform data to column-oriented format
        batch_data = {}
        for col in column_names:
            batch_data[col] = []
            for source in sources:
                source_dict = source.model_dump()
                batch_data[col].append(source_dict.get(col))
        
        # Use VAST's native batch insert functionality
        success = await store.db_manager.insert_batch_efficient(
            table_name="sources",
            data=batch_data,
            batch_size=len(sources)
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to insert sources batch")
        
        logger.info(f"Successfully created {len(sources)} sources using VAST batch insert")
        return sources
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create sources batch: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# DELETE endpoint
@router.delete("/sources/{source_id}")
async def delete_source_by_id(
    source_id: str,
    soft_delete: bool = Query(True, description="Use soft delete"),
    cascade: bool = Query(True, description="Cascade delete related flows"),
    deleted_by: str = Query("system", description="User performing the deletion"),
    store: VASTStore = Depends(get_vast_store)
):
    """Delete a source"""
    try:
        success = await delete_source(store, source_id, soft_delete, cascade, deleted_by)
        if not success:
            raise HTTPException(status_code=404, detail="Source not found")
        return {"message": "Source deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete source {source_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Source tags endpoints
@router.head("/sources/{source_id}/tags")
async def head_source_tags(source_id: str):
    """Return Source tags path headers"""
    return {}

@router.get("/sources/{source_id}/tags", response_model=Tags)
async def list_source_tags(
    source_id: str,
    store: VASTStore = Depends(get_vast_store)
):
    """List Source Tags"""
    try:
        source = await get_source(store, source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        
        # Return the source tags or empty dict if no tags
        return source.tags or Tags()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list source tags for {source_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/sources/{source_id}/tags", response_model=Tags)
async def update_source_tags(
    source_id: str,
    tags: Tags,
    store: VASTStore = Depends(get_vast_store)
):
    """Update Source Tags"""
    try:
        source = await get_source(store, source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        
        # Update source tags
        success = await store.update_source_tags(source_id, tags)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update source tags")
        
        return tags
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update source tags for {source_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.head("/sources/{source_id}/tags/{name}")
async def head_source_tag(source_id: str, name: str):
    """Return Source tag path headers"""
    return {}

@router.get("/sources/{source_id}/tags/{name}", response_model=str)
async def get_source_tag(
    source_id: str,
    name: str,
    store: VASTStore = Depends(get_vast_store)
):
    """Source Tag Value"""
    try:
        source = await get_source(store, source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        
        # Get specific tag value
        if source.tags and name in source.tags:
            return source.tags[name]
        else:
            raise HTTPException(status_code=404, detail="Tag not found")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get source tag {name} for {source_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/sources/{source_id}/tags/{name}", status_code=204)
async def update_source_tag(
    source_id: str,
    name: str,
    value: str = Body(..., media_type="text/plain"),
    store: VASTStore = Depends(get_vast_store)
):
    """Update Source Tag Value"""
    try:
        source = await get_source(store, source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        
        # Update specific tag
        current_tags = source.tags or {}
        current_tags[name] = value
        
        success = await store.update_source_tags(source_id, Tags(**current_tags))
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update source tag")
        
        return  # 204 No Content
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update source tag {name} for {source_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/sources/{source_id}/tags/{name}", status_code=204)
async def delete_source_tag(
    source_id: str,
    name: str,
    store: VASTStore = Depends(get_vast_store)
):
    """Delete Source Tag"""
    try:
        source = await get_source(store, source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        
        # Remove specific tag
        current_tags = source.tags or {}
        if name in current_tags:
            del current_tags[name]
            success = await store.update_source_tags(source_id, Tags(**current_tags))
            if not success:
                raise HTTPException(status_code=500, detail="Failed to delete source tag")
        
        return  # 204 No Content
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete source tag {name} for {source_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")



@router.head("/sources/{source_id}/description")
async def head_source_description(source_id: str):
    """Return source description path headers"""
    return {}

@router.get("/sources/{source_id}/description")
async def get_source_description(
    source_id: str,
    store: VASTStore = Depends(get_vast_store)
):
    """Get source description"""
    try:
        source = await get_source(store, source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        return source.description or ""
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get source description for {source_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/sources/{source_id}/description")
async def update_source_description(
    source_id: str,
    description: str,
    store: VASTStore = Depends(get_vast_store)
):
    """Update source description"""
    try:
        source = await get_source(store, source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        
        source.description = description
        success = await store.update_source(source_id, source)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update source description")
        
        return {"message": "Description updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update source description for {source_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/sources/{source_id}/description")
async def delete_source_description(
    source_id: str,
    store: VASTStore = Depends(get_vast_store)
):
    """Delete source description"""
    try:
        source = await get_source(store, source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        
        source.description = None
        
        # Save the updated source
        success = await store.update_source(source_id, source)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete source description")
        
        return {"message": "Description deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete source description for {source_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.head("/sources/{source_id}/label")
async def head_source_label(source_id: str):
    """Return source label path headers"""
    return {}

@router.get("/sources/{source_id}/label")
async def get_source_label(
    source_id: str,
    store: VASTStore = Depends(get_vast_store)
):
    """Get source label"""
    try:
        source = await get_source(store, source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        return source.label or ""
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get source label for {source_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/sources/{source_id}/label")
async def update_source_label(
    source_id: str,
    label: str,
    store: VASTStore = Depends(get_vast_store)
):
    """Update source label"""
    try:
        source = await get_source(store, source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        
        source.label = label
        success = await store.update_source(source_id, source)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update source label")
        
        return {"message": "Label updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update source label for {source_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/sources/{source_id}/label")
async def delete_source_label(
    source_id: str,
    store: VASTStore = Depends(get_vast_store)
):
    """Delete source label"""
    try:
        source = await get_source(store, source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        
        source.label = None
        
        # Save the updated source
        success = await store.update_source(source_id, source)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete source label")
        
        return {"message": "Label deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete source label for {source_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

 