from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from app.models import Source, SourcesResponse, SourceFilters
from app.sources import get_sources, get_source, create_source, delete_source
from app.vast_store import VASTStore
from app.dependencies import get_vast_store
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# HEAD endpoints
@router.head("/sources")
async def head_sources():
    """Return sources path headers"""
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

# Individual field endpoints
@router.head("/sources/{source_id}/tags")
async def head_source_tags(source_id: str):
    """Return source tags path headers"""
    return {}

@router.get("/sources/{source_id}/tags")
async def get_source_tags(
    source_id: str,
    store: VASTStore = Depends(get_vast_store)
):
    """Get source tags"""
    try:
        source = await get_source(store, source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        return source.tags.root if source.tags else {}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get source tags for {source_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.head("/sources/{source_id}/tags/{name}")
async def head_source_tag(source_id: str, name: str):
    """Return source tag path headers"""
    return {}

@router.get("/sources/{source_id}/tags/{name}")
async def get_source_tag(
    source_id: str,
    name: str,
    store: VASTStore = Depends(get_vast_store)
):
    """Get specific source tag value"""
    try:
        source = await get_source(store, source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        if not source.tags or name not in source.tags:
            raise HTTPException(status_code=404, detail="Tag not found")
        return source.tags[name]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get source tag {name} for {source_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/sources/{source_id}/tags/{name}")
async def update_source_tag(
    source_id: str,
    name: str,
    value: str,
    store: VASTStore = Depends(get_vast_store)
):
    """Create or update source tag"""
    try:
        source = await get_source(store, source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        
        # Update the tag
        if not source.tags:
            source.tags = {}
        source.tags[name] = value
        
        # Save the updated source
        success = await store.update_source(source_id, source)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update source tag")
        
        return {"message": "Tag updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update source tag {name} for {source_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

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

 