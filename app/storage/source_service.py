"""
Source Storage Service

This module handles all source-related storage operations including
CRUD operations, filtering, and collection management.
"""

import logging
from typing import List, Optional
from datetime import datetime, timezone

from fastapi import HTTPException
from .interfaces import StorageInterface
from ..models import Source, SourceFilters, Tags, CollectionItem

logger = logging.getLogger(__name__)


class SourceStorageService:
    """Handles source-related storage operations"""
    
    def __init__(self, vast_db, s3_client):
        self.vast_db = vast_db
        self.s3_client = s3_client
    
    async def get_sources(self, filters: SourceFilters) -> List[Source]:
        """Get sources with filtering"""
        try:
            # Build query using vaststore
            query = self.vast_db.query("sources").select("*")
            
            # Add filters
            if filters.label:
                query = query.where(f"label = '{filters.label}'")
            if filters.format:
                query = query.where(f"format = '{filters.format}'")
            
            # Add limit
            if filters.limit:
                query = query.limit(filters.limit)
            
            result = query.execute()
            
            # Convert to Source objects
            sources = []
            for row in result:
                source_data = dict(row)
                sources.append(Source(**source_data))
            
            return sources
        except Exception as e:
            logger.error("Failed to get sources: %s", e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def get_source(self, source_id: str) -> Optional[Source]:
        """Get a specific source by ID"""
        try:
            result = self.vast_db.query("sources").select("*").where(f"id = '{source_id}'").execute()
            
            if not result or len(result) == 0:
                return None
            
            source_data = dict(result[0])
            return Source(**source_data)
        except Exception as e:
            logger.error("Failed to get source %s: %s", source_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def create_source(self, source: Source) -> bool:
        """Create a new source"""
        try:
            now = datetime.now(timezone.utc)
            source.created = now
            source.updated = now
            
            source_data = source.model_dump()
            self.vast_db.insert_record("sources", source_data)
            return True
        except Exception as e:
            logger.error("Failed to create source: %s", e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def update_source(self, source_id: str, source: Source) -> bool:
        """Update an existing source"""
        try:
            source.updated = datetime.now(timezone.utc)
            source_data = source.model_dump()
            
            self.vast_db.query("sources").update().set(**source_data).where(f"id = '{source_id}'").execute()
            return True
        except Exception as e:
            logger.error("Failed to update source %s: %s", source_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def delete_source(self, source_id: str, cascade: bool = True) -> bool:
        """Delete a source"""
        try:
            # Check for dependencies if cascade is False
            if not cascade:
                # Check if source has flows
                flows_result = self.vast_db.query("flows").select("id").where(f"source_id = '{source_id}'").execute()
                if flows_result and len(flows_result) > 0:
                    raise ValueError("Cannot delete source with existing flows. Use cascade=True to delete flows first.")
            
            # Delete source
            self.vast_db.query("sources").delete().where(f"id = '{source_id}'").execute()
            return True
        except ValueError as e:
            # Re-raise constraint violations
            raise e
        except Exception as e:
            logger.error("Failed to delete source %s: %s", source_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def get_source_collections(self, source_id: str) -> List[CollectionItem]:
        """Get source collections"""
        try:
            result = self.vast_db.query("source_collections").select("*").where(f"source_id = '{source_id}'").execute()
            
            collections = []
            for row in result:
                collection_data = dict(row)
                collections.append(CollectionItem(**collection_data))
            
            return collections
        except Exception as e:
            logger.error("Failed to get source collections for %s: %s", source_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def add_source_to_collection(self, collection_id: str, source_id: str, label: str, description: str) -> bool:
        """Add source to collection"""
        try:
            collection_data = {
                "collection_id": collection_id,
                "source_id": source_id,
                "label": label,
                "description": description
            }
            self.vast_db.insert_record("source_collections", collection_data)
            return True
        except Exception as e:
            logger.error("Failed to add source %s to collection %s: %s", source_id, collection_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def remove_source_from_collection(self, collection_id: str, source_id: str) -> bool:
        """Remove source from collection"""
        try:
            self.vast_db.query("source_collections").delete().where(
                f"collection_id = '{collection_id}' AND source_id = '{source_id}'"
            ).execute()
            return True
        except Exception as e:
            logger.error("Failed to remove source %s from collection %s: %s", source_id, collection_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")
