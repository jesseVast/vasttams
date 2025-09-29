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
            
            # Handle VAST query result format
            tags_data = None
            if isinstance(result, dict) and 'data' in result:
                data = result['data']
                if isinstance(data, dict) and 'tags' in data and data['tags']:
                    tags_data = data['tags'][0] if data['tags'] else None
                elif isinstance(data, list) and data:
                    tags_data = data[0].get('tags') if hasattr(data[0], 'get') else None
            elif isinstance(result, list) and result:
                tags_data = result[0].get('tags') if hasattr(result[0], 'get') else None
            
            # Parse JSON string if needed
            if isinstance(tags_data, str):
                import json
                try:
                    tags_data = json.loads(tags_data)
                except (json.JSONDecodeError, TypeError):
                    tags_data = None
            
            return Tags(tags_data) if tags_data else None
        except Exception as e:
            logger.error("Failed to get source tags for %s: %s", source_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def update_source_tags(self, source_id: str, tags: Tags) -> bool:
        """Update source tags"""
        try:
            # Update the source with new tags - serialize as JSON string
            import json
            tags_json = json.dumps(tags.root) if tags and tags.root else "{}"
            self.vast_db.query("sources").update().set(tags=tags_json).where(f"id = '{source_id}'").execute()
            return True
        except Exception as e:
            logger.error("Failed to update source tags for %s: %s", source_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def get_source_tag(self, source_id: str, name: str) -> Optional[str]:
        """Get a specific source tag"""
        try:
            tags = await self.get_source_tags(source_id)
            if tags and hasattr(tags, 'root') and tags.root:
                return tags.root.get(name)
            return None
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
            
            # Update the specific tag in the root dictionary
            if not current_tags.root:
                current_tags.root = {}
            current_tags.root[name] = value
            
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
            if not current_tags or not current_tags.root or name not in current_tags.root:
                return False
            
            # Remove the specific tag from the root dictionary
            del current_tags.root[name]
            
            # Save updated tags
            return await self.update_source_tags(source_id, current_tags)
        except Exception as e:
            logger.error("Failed to delete source tag %s for %s: %s", name, source_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    # Flow tag methods
    async def get_flow_tags(self, flow_id: str) -> Optional[Tags]:
        """Get flow tags"""
        try:
            # Get flow first to access tags
            result = self.vast_db.query("flows").select("tags").where(f"id = '{flow_id}'").execute()
            
            logger.debug("get_flow_tags query result for %s: %s", flow_id, result)
            
            # Handle different result formats
            if isinstance(result, dict):
                if 'data' in result:
                    data = result['data']
                elif 'error' in result:
                    logger.error("VAST query error for flow %s: %s", flow_id, result['error'])
                    raise HTTPException(status_code=500, detail="Database query error")
                else:
                    data = result
            else:
                data = result
            
            if not data or len(data) == 0:
                logger.warning("No flow found for flow_id %s", flow_id)
                raise HTTPException(status_code=404, detail="Flow not found")
            
            tags_data = data[0].get('tags') if isinstance(data, list) else data.get('tags')
            if not tags_data:
                return None
            
            # Parse JSON string back to Tags object
            import json
            if isinstance(tags_data, str):
                tags_dict = json.loads(tags_data)
            elif isinstance(tags_data, list):
                # Handle case where tags is returned as a list
                if len(tags_data) == 1 and tags_data[0] is None:
                    return None
                tags_dict = tags_data[0] if tags_data else {}
            else:
                tags_dict = tags_data
            
            # Ensure tags_dict is a dictionary
            if not isinstance(tags_dict, dict):
                logger.warning("Tags data is not a dictionary: %s", tags_dict)
                return None
            
            tags_obj = Tags(tags_dict)
            logger.debug("Created Tags object: %s, root: %s", tags_obj, tags_obj.root)
            return tags_obj
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Failed to get flow tags for %s: %s", flow_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def update_flow_tags(self, flow_id: str, tags: Tags) -> bool:
        """Update flow tags"""
        try:
            import json
            import asyncio
            tags_json = json.dumps(tags.root)
            logger.debug("Updating flow %s tags with JSON: %s", flow_id, tags_json)
            
            result = self.vast_db.query("flows").update().set(tags=tags_json).where(f"id = '{flow_id}'").execute()
            logger.debug("Update query result for flow %s: %s", flow_id, result)
            
            # Add a small delay to allow the update to be committed
            await asyncio.sleep(0.1)
            
            return True
        except Exception as e:
            logger.error("Failed to update flow tags for %s: %s", flow_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def update_flow_tag(self, flow_id: str, name: str, value: str) -> bool:
        """Update a single flow tag"""
        try:
            # Get current tags
            current_tags = await self.get_flow_tags(flow_id)
            if current_tags is None:
                current_tags = Tags({})
            
            logger.debug("Current tags for flow %s: %s", flow_id, current_tags.root if current_tags else "None")
            
            # Update the specific tag
            current_tags[name] = value
            
            logger.debug("Updated tags for flow %s: %s", flow_id, current_tags.root)
            
            # Save updated tags
            result = await self.update_flow_tags(flow_id, current_tags)
            logger.debug("Update result for flow %s: %s", flow_id, result)
            return result
        except Exception as e:
            logger.error("Failed to update flow tag %s for %s: %s", name, flow_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def delete_flow_tag(self, flow_id: str, name: str) -> bool:
        """Delete a single flow tag"""
        try:
            # Get current tags
            current_tags = await self.get_flow_tags(flow_id)
            if current_tags is None or name not in current_tags:
                return False
            
            # Remove the tag
            del current_tags[name]
            
            # Save updated tags
            return await self.update_flow_tags(flow_id, current_tags)
        except Exception as e:
            logger.error("Failed to delete flow tag %s for %s: %s", name, flow_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")