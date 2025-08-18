"""
Sources submodule for TAMS API.
Handles source-related operations and business logic.
"""
from typing import List, Optional, Dict
from fastapi import HTTPException
from datetime import datetime, timezone
from ..models.models import Source, SourcesResponse, PagingInfo, Tags, SourceFilters
from ..storage.vast_store import VASTStore
import logging
import uuid

logger = logging.getLogger(__name__)

# Standalone functions for router use
async def get_sources(store: VASTStore, filters: SourceFilters) -> List[Source]:
    """Get sources with filtering"""
    try:
        filter_dict = {}
        if filters.label:
            filter_dict['label'] = filters.label
        if filters.format:
            filter_dict['format'] = filters.format
        
        sources = await store.list_sources(filters=filter_dict, limit=filters.limit)
        return sources
    except Exception as e:
        logger.error("Failed to get sources: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")

async def get_source(store: VASTStore, source_id: str) -> Optional[Source]:
    """Get a specific source by ID"""
    try:
        source = await store.get_source(source_id)
        return source
    except Exception as e:
        logger.error("Failed to get source %s: %s", source_id, e)
        raise HTTPException(status_code=500, detail="Internal server error")

async def create_source(store: VASTStore, source: Source) -> bool:
    """Create a new source"""
    try:
        now = datetime.now(timezone.utc)
        source.created = now
        source.metadata_updated = now
        success = await store.create_source(source)
        return success
    except Exception as e:
        logger.error("Failed to create source: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")

async def delete_source(store: VASTStore, source_id: str, cascade: bool = True) -> bool:
    """Delete a source (hard delete only - TAMS compliant)"""
    try:
        success = await store.delete_source(source_id, cascade=cascade)
        return success
    except ValueError as e:
        # Handle the case where source deletion is not allowed (immutable)
        logger.warning("Source deletion not allowed: %s", e)
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error("Failed to delete source %s: %s", source_id, e)
        raise HTTPException(status_code=500, detail="Internal server error")

class SourceManager:
    """Manager for source operations (create, retrieve, update, delete, etc.)."""
    def __init__(self, store: Optional[VASTStore] = None):
        self.store = store

    async def list_sources(self, filters: Dict, limit: int, store: Optional[VASTStore] = None) -> SourcesResponse:
        store = store or self.store
        if store is None:
            raise HTTPException(status_code=500, detail="VAST store is not initialized")
        try:
            sources = await store.list_sources(filters=filters, limit=limit)
            paging = None
            if len(sources) == limit:
                paging = None  # PagingInfo can be added if needed
            return SourcesResponse(data=sources, paging=paging)
        except Exception as e:
            logger.error("Failed to list sources: %s", e)
            raise HTTPException(status_code=500, detail="Internal server error")

    async def get_source(self, source_id: str, store: Optional[VASTStore] = None) -> Source:
        store = store or self.store
        if store is None:
            raise HTTPException(status_code=500, detail="VAST store is not initialized")
        try:
            source = await store.get_source(source_id)
            if not source:
                raise HTTPException(status_code=404, detail="Source not found")
            return source
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Failed to get source %s: %s", source_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")

    async def create_source(self, source: Source, store: Optional[VASTStore] = None) -> Source:
        store = store or self.store
        if store is None:
            raise HTTPException(status_code=500, detail="VAST store is not initialized")
        try:
            now = datetime.now(timezone.utc)
            source.created = now
            source.metadata_updated = now
            success = await store.create_source(source)
            if not success:
                raise HTTPException(status_code=500, detail="Failed to create source")
            return source
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Failed to create source: %s", e)
            raise HTTPException(status_code=500, detail="Internal server error")

    async def delete_source(self, source_id: str, store: Optional[VASTStore] = None, cascade: bool = True):
        store = store or self.store
        if store is None:
            raise HTTPException(status_code=500, detail="VAST store is not initialized")
        try:
            success = await store.delete_source(source_id, cascade=cascade)
            if not success:
                raise HTTPException(status_code=404, detail="Source not found")
            
            cascade_msg = " with cascade" if cascade else ""
            return {"message": f"Source hard deleted{cascade_msg}"}
        except ValueError as e:
            # Handle the case where source deletion is not allowed (immutable)
            logger.warning("Source deletion not allowed: %s", e)
            raise HTTPException(status_code=403, detail=str(e))
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Failed to delete source %s: %s", source_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")

    async def update_source(self, source_id: str, source: Source, store: Optional[VASTStore] = None) -> Source:
        """
        Update an existing source with new data.

        Args:
            source_id (str): The unique identifier of the source to update.
            source (Source): The updated source object.
            store (Optional[VASTStore]): Optional VASTStore instance to use. Defaults to the manager's store.

        Returns:
            Source: The updated source object.

        Raises:
            HTTPException: 404 if the source is not found, 500 for internal errors or if the store is not initialized.
        """
        store = store or self.store
        if store is None:
            raise HTTPException(status_code=500, detail="VAST store is not initialized")
        
        try:
            # Update the timestamp
            source.metadata_updated = datetime.now(timezone.utc)
            
            # Update in store
            success = await store.update_source(source_id, source)
            if not success:
                raise HTTPException(status_code=404, detail="Source not found")
            
            return source
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Failed to update source %s: %s", source_id, e)
            raise HTTPException(status_code=500, detail="Internal server error") 