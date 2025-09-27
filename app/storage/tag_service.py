"""
Tag Storage Service

This module handles all tag-related storage operations including
CRUD operations for source tags and tag management.
"""

import logging
from typing import Optional

from fastapi import HTTPException
from .interfaces import StorageInterface
from ..models import Tags

logger = logging.getLogger(__name__)


class TagStorageService:
    """Handles tag-related storage operations"""
    
    def __init__(self, vast_db, s3_client):
        self.vast_db = vast_db
        self.s3_client = s3_client
    
    async def get_source_tags(self, source_id: str) -> Optional[Tags]:
        """Get source tags"""
        try:
            # Get source first to access tags
            result = self.vast_db.query("sources").select("tags").where(f"id = '{source_id}'").execute()
            if not result or len(result) == 0:
                return None
            
            tags_data = result[0].get('tags')
            return Tags(tags_data) if tags_data else None
        except Exception as e:
            logger.error("Failed to get source tags for %s: %s", source_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def update_source_tags(self, source_id: str, tags: Tags) -> bool:
        """Update source tags"""
        try:
            # Update the source with new tags
            self.vast_db.query("sources").update().set(tags=tags.model_dump()).where(f"id = '{source_id}'").execute()
            return True
        except Exception as e:
            logger.error("Failed to update source tags for %s: %s", source_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def get_source_tag(self, source_id: str, name: str) -> Optional[str]:
        """Get a specific source tag"""
        try:
            tags = await self.get_source_tags(source_id)
            return tags.get(name) if tags else None
        except Exception as e:
            logger.error("Failed to get source tag %s for %s: %s", name, source_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def update_source_tag(self, source_id: str, name: str, value: str) -> bool:
        """Update a specific source tag"""
        try:
            # Get current tags
            current_tags = await self.get_source_tags(source_id)
            if not current_tags:
                current_tags = Tags({})
            
            # Update the specific tag
            current_tags[name] = value
            
            # Save updated tags
            return await self.update_source_tags(source_id, current_tags)
        except Exception as e:
            logger.error("Failed to update source tag %s for %s: %s", name, source_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def delete_source_tag(self, source_id: str, name: str) -> bool:
        """Delete a specific source tag"""
        try:
            # Get current tags
            current_tags = await self.get_source_tags(source_id)
            if not current_tags or name not in current_tags:
                return False
            
            # Remove the specific tag
            del current_tags[name]
            
            # Save updated tags
            return await self.update_source_tags(source_id, current_tags)
        except Exception as e:
            logger.error("Failed to delete source tag %s for %s: %s", name, source_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")
