from fastapi import APIRouter, Depends, HTTPException, Query, Body, Request
from typing import List, Optional, Dict, Any
from app.models import Source, SourcesResponse, SourceFilters, Tags
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
    request: Request = None,  # To access all query parameters for tag filtering
    store: VASTStore = Depends(get_vast_store)
):
    """List sources with optional filtering including tag-based filtering"""
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
        
        filters = SourceFilters(
            label=label,
            format=format,
            page=page,
            limit=limit,
            tag_filters=tag_filters if tag_filters else None,
            tag_exists_filters=tag_exists_filters if tag_exists_filters else None
        )
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
    value: str = Body(..., description="Tag value"),
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

@router.delete("/sources/{source_id}/tags/{name}")
async def delete_source_tag(
    source_id: str,
    name: str,
    store: VASTStore = Depends(get_vast_store)
):
    """Delete specific source tag"""
    try:
        source = await get_source(store, source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        
        if not source.tags or name not in source.tags:
            raise HTTPException(status_code=404, detail="Tag not found")
        
        # Remove the tag
        if source.tags and name in source.tags:
            # Create a new dict without the deleted tag
            new_tags = dict(source.tags.root)
            del new_tags[name]
            source.tags = Tags(root=new_tags)
        
        # Save the updated source
        success = await store.update_source(source_id, source)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete source tag")
        
        return {"message": "Tag deleted successfully"}
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

 