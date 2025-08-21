from fastapi import APIRouter, Depends, HTTPException, Query, Body
from typing import List, Optional
import uuid
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
        logger.error("Failed to list sources: %s", e)
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
        logger.error("Failed to get source %s: %s", source_id, e)
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
        logger.error("Failed to create source: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")

# Batch POST endpoint
@router.post("/sources/batch", response_model=List[Source], status_code=201)
async def create_sources_batch(
    sources: List[Source],
    store: VASTStore = Depends(get_vast_store)
):
    """Create multiple sources using conditional logic: single insert for 1 source, batch insert for multiple"""
    try:
        if not sources:
            raise HTTPException(status_code=400, detail="No sources provided")
        
        # If only 1 source, use single source creation
        if len(sources) == 1:
            success = await create_source(store, sources[0])
            if not success:
                raise HTTPException(status_code=500, detail="Failed to create single source")
            logger.info("Successfully created 1 source using single insert")
            return sources
        
        # For multiple sources, use VAST's native batch insert
        logger.info("Using VAST batch insert for %d sources", len(sources))
        
        # Convert Pydantic models to the format expected by insert_batch_efficient
        # The method expects Dict[str, List[Any]] where keys are column names
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
        rows_inserted = store.db_manager.insert_batch_efficient(
            table_name="sources",
            data=batch_data,
            batch_size=len(sources)
        )
        
        if rows_inserted <= 0:
            raise HTTPException(status_code=500, detail="Failed to insert sources batch")
        
        logger.info("Successfully created %d sources using VAST batch insert", rows_inserted)
        return sources
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to create sources batch: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")

# Source Collection Management Endpoints
@router.get("/sources/{source_id}/source_collection")
async def get_source_collection(
    source_id: str,
    store: VASTStore = Depends(get_vast_store)
):
    """Get source collection - dynamically computed from source_collections table"""
    try:
        # Get collections dynamically from the source_collections table
        collections = await store.get_source_collections(source_id)
        
        # Return collection IDs for backward compatibility
        collection_ids = [col.collection_id for col in collections]
        return collection_ids
        
    except Exception as e:
        logger.error("Failed to get source collection for %s: %s", source_id, e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/sources/{source_id}/source_collection")
async def update_source_collection(
    source_id: str,
    source_collection: List[str],
    store: VASTStore = Depends(get_vast_store)
):
    """Update source collection - now managed dynamically via source_collections table"""
    try:
        # Check if source exists
        source = await get_source(store, source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        
        # Get current collections
        current_collections = await store.get_source_collections(source_id)
        current_collection_ids = [col.collection_id for col in current_collections]
        
        # Remove sources from collections they're no longer in
        for collection_id in current_collection_ids:
            if collection_id not in source_collection:
                await store.remove_source_from_collection(collection_id, source_id)
        
        # Add sources to new collections
        for collection_id in source_collection:
            if collection_id not in current_collection_ids:
                # Generate a default label and description
                label = f"Collection {collection_id[:8]}"
                description = f"Auto-generated collection for source {source_id[:8]}"
                await store.add_source_to_collection(collection_id, source_id, label, description)
        
        return {"message": "Source collection updated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update source collection for %s: %s", source_id, e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.head("/sources/{source_id}/source_collection")
async def head_source_collection(source_id: str):
    """Return source collection path headers"""
    return {}


# Source Collection CRUD Endpoints
@router.post("/source-collections")
async def create_source_collection(
    collection_id: str,
    label: str,
    description: Optional[str] = None,
    store: VASTStore = Depends(get_vast_store)
):
    """Create a new source collection"""
    try:
        # Add a dummy source to create the collection (will be removed if no sources)
        dummy_source_id = str(uuid.uuid4())
        success = await store.add_source_to_collection(
            collection_id, 
            dummy_source_id, 
            label, 
            description
        )
        
        if success:
            # Remove the dummy source
            await store.remove_source_from_collection(collection_id, dummy_source_id)
            return {"message": f"Source collection {collection_id} created successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to create source collection")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to create source collection %s: %s", collection_id, e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/source-collections/{collection_id}/sources")
async def get_source_collection_sources(
    collection_id: str,
    store: VASTStore = Depends(get_vast_store)
):
    """Get all sources in a source collection"""
    try:
        sources = await store.get_collection_sources(collection_id)
        return {"collection_id": collection_id, "sources": sources}
        
    except Exception as e:
        logger.error("Failed to get sources for collection %s: %s", collection_id, e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/source-collections/{collection_id}")
async def delete_source_collection(
    collection_id: str,
    store: VASTStore = Depends(get_vast_store)
):
    """Delete a source collection and remove all source associations"""
    try:
        success = await store.delete_source_collection(collection_id)
        if success:
            return {"message": f"Source collection {collection_id} deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail="Source collection not found")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete source collection %s: %s", collection_id, e)
        raise HTTPException(status_code=500, detail="Internal server error")

# DELETE endpoint
@router.delete("/sources/{source_id}")
async def delete_source_by_id(
    source_id: str,
    cascade: bool = Query(True, description="Cascade delete related flows"),
    store: VASTStore = Depends(get_vast_store)
):
    """Delete a source (hard delete only - TAMS compliant)"""
    try:
        success = await delete_source(store, source_id, cascade)
        if not success:
            raise HTTPException(status_code=404, detail="Source not found")
        return {"message": "Source hard deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete source %s: %s", source_id, e)
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
        logger.error("Failed to list source tags for %s: %s", source_id, e)
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
        logger.error("Failed to update source tags for %s: %s", source_id, e)
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
        logger.error("Failed to get source tag %s for %s: %s", name, source_id, e)
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
        logger.error("Failed to update source tag %s for %s: %s", name, source_id, e)
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
        current_tags = source.tags.root if source.tags else {}
        if name in current_tags:
            # Create a new dictionary without the tag to delete
            new_tags = {k: v for k, v in current_tags.items() if k != name}
            success = await store.update_source_tags(source_id, Tags(**new_tags))
            if not success:
                raise HTTPException(status_code=500, detail="Failed to delete source tag")
        
        return  # 204 No Content
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete source tag %s for %s: %s", name, source_id, e)
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
        logger.error("Failed to get source description for %s: %s", source_id, e)
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
        logger.error("Failed to update source description for %s: %s", source_id, e)
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
        logger.error("Failed to delete source description for %s: %s", source_id, e)
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
        logger.error("Failed to get source label for %s: %s", source_id, e)
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
        logger.error("Failed to update source label for %s: %s", source_id, e)
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
        logger.error("Failed to delete source label for %s: %s", source_id, e)
        raise HTTPException(status_code=500, detail="Internal server error")

 