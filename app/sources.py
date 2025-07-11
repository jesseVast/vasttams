"""
Sources submodule for TAMS API.
Handles source-related operations and business logic.
"""
from typing import List, Optional, Dict
from fastapi import HTTPException
from datetime import datetime, timezone
from .models import Source, SourcesResponse, PagingInfo, Tags
from .vast_store import VASTStore
import logging
import uuid

logger = logging.getLogger(__name__)

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
            logger.error(f"Failed to list sources: {e}")
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
            logger.error(f"Failed to get source {source_id}: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

    async def create_source(self, source: Source, store: Optional[VASTStore] = None) -> Source:
        store = store or self.store
        if store is None:
            raise HTTPException(status_code=500, detail="VAST store is not initialized")
        try:
            now = datetime.now(timezone.utc)
            source.created = now
            source.updated = now
            success = await store.create_source(source)
            if not success:
                raise HTTPException(status_code=500, detail="Failed to create source")
            return source
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to create source: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

    async def delete_source(self, source_id: str, store: Optional[VASTStore] = None):
        store = store or self.store
        if store is None:
            raise HTTPException(status_code=500, detail="VAST store is not initialized")
        try:
            success = await store.delete_source(source_id)
            if not success:
                raise HTTPException(status_code=404, detail="Source not found")
            return {"message": "Source deleted"}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to delete source {source_id}: {e}")
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
            existing_source = await store.get_source(source_id)
            if not existing_source:
                raise HTTPException(status_code=404, detail="Source not found")
            source.id = existing_source.id
            source.updated = datetime.now(timezone.utc)
            success = await store.update_source(source)
            if not success:
                raise HTTPException(status_code=500, detail="Failed to update source")
            return source
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to update source {source_id}: {e}")
            raise HTTPException(status_code=500, detail="Internal server error") 