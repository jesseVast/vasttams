from fastapi import APIRouter, Depends, Query, HTTPException
from typing import List, Optional
from .models import Source, SourcesResponse
from .vast_store import VASTStore
from .dependencies import get_vast_store
from .sources import SourceManager
import logging

router = APIRouter()
logger = logging.getLogger(__name__)
source_manager = SourceManager()

@router.head("/sources")
async def head_sources():
    """Return sources path headers."""
    logger.info("HEAD /sources called")
    return {}

@router.get("/sources", response_model=SourcesResponse)
async def list_sources(
    label: Optional[str] = Query(None, description="Filter by label"),
    format: Optional[str] = Query(None, description="Filter by format"),
    page: Optional[str] = Query(None, description="Pagination key"),
    limit: Optional[int] = Query(100, ge=1, le=1000, description="Number of results"),
    store: VASTStore = Depends(get_vast_store)
):
    """List sources with optional filtering."""
    logger.info(f"GET /sources called with label={label}, format={format}")
    filters = {}
    if label:
        filters['label'] = label
    if format:
        filters['format'] = format
    return await source_manager.list_sources(filters, limit or 100, store)

@router.head("/sources/{source_id}")
async def head_source(source_id: str):
    """Return source path headers."""
    logger.info(f"HEAD /sources/{source_id} called")
    return {}

@router.get("/sources/{source_id}", response_model=Source)
async def get_source(source_id: str, store: VASTStore = Depends(get_vast_store)):
    """Get source by ID."""
    logger.info(f"GET /sources/{source_id} called")
    return await source_manager.get_source(source_id, store)

@router.post("/sources", response_model=Source, status_code=201)
async def create_source(source: Source, store: VASTStore = Depends(get_vast_store)):
    """Create a new source."""
    logger.info(f"POST /sources called")
    return await source_manager.create_source(source, store)

@router.delete("/sources/{source_id}")
async def delete_source(source_id: str, store: VASTStore = Depends(get_vast_store)):
    """Delete a source by its unique identifier."""
    logger.info(f"DELETE /sources/{source_id} called")
    return await source_manager.delete_source(source_id, store) 