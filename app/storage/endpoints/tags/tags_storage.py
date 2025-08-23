"""
Tags Storage Module for TAMS API

This module handles tag operations for sources and flows using a dedicated tags table.
Tags are now stored as dynamic fields in a separate table rather than JSON strings.
"""

import logging
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from ibis import _

from ....models.models import Tags
from ...vastdbmanager import VastDBManager

logger = logging.getLogger(__name__)


class TagsStorage:
    """
    Tags storage manager for TAMS API
    
    Handles CRUD operations for tags stored in the dedicated tags table.
    Tags can be associated with sources or flows (entities).
    """
    
    def __init__(self, vast_db_manager: VastDBManager):
        """
        Initialize tags storage
        
        Args:
            vast_db_manager: VAST database manager instance
        """
        self.vast_db_manager = vast_db_manager
        self.table_name = 'tags'
    
    async def get_tags(self, entity_type: str, entity_id: str) -> Optional[Tags]:
        """
        Get all tags for a specific entity (source or flow)
        
        Args:
            entity_type: Type of entity ('source' or 'flow')
            entity_id: ID of the entity
            
        Returns:
            Tags object or None if no tags found
        """
        try:
            # Build VAST predicate for entity lookup
            predicate = (_.entity_type == entity_type) & (_.entity_id == entity_id)
            
            # Query tags table using VAST select method
            result = self.vast_db_manager.select(
                self.table_name, 
                predicate=predicate, 
                output_by_row=True,
                columns=['tag_name', 'tag_value']
            )
            
            if not result or len(result) == 0:
                return None
            
            # Convert result to Tags object
            tags_dict = {}
            for row in result:
                tag_name = row.get('tag_name')
                tag_value = row.get('tag_value')
                if tag_name and tag_value:
                    tags_dict[tag_name] = tag_value
            
            return Tags(tags_dict) if tags_dict else None
            
        except Exception as e:
            logger.error("Failed to get tags for %s %s: %s", entity_type, entity_id, e)
            return None
    
    async def get_tag(self, entity_type: str, entity_id: str, tag_name: str) -> Optional[str]:
        """
        Get a specific tag value for an entity
        
        Args:
            entity_type: Type of entity ('source' or 'flow')
            entity_id: ID of the entity
            tag_name: Name of the tag to retrieve
            
        Returns:
            Tag value or None if not found
        """
        try:
            # Build VAST predicate for specific tag lookup
            predicate = (_.entity_type == entity_type) & (_.entity_id == entity_id) & (_.tag_name == tag_name)
            
            # Query tags table using VAST select method
            result = self.vast_db_manager.select(
                self.table_name, 
                predicate=predicate, 
                output_by_row=True,
                columns=['tag_value']
            )
            
            if not result or len(result) == 0:
                return None
            
            return result[0].get('tag_value')
            
        except Exception as e:
            logger.error("Failed to get tag %s for %s %s: %s", tag_name, entity_type, entity_id, e)
            return None
    
    async def create_tag(self, entity_type: str, entity_id: str, tag_name: str, tag_value: str, 
                        created_by: Optional[str] = None) -> bool:
        """
        Create a new tag for an entity
        
        Args:
            entity_type: Type of entity ('source' or 'flow')
            entity_id: ID of the entity
            tag_name: Name of the tag
            tag_value: Value of the tag
            created_by: User who created the tag
            
        Returns:
            bool: True if creation successful, False otherwise
        """
        try:
            logger.info("🔍 DEBUG: Starting tag creation for %s %s: %s=%s", entity_type, entity_id, tag_name, tag_value)
            
            tag_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc)
            
            tag_data = {
                'id': tag_id,
                'entity_type': entity_type,
                'entity_id': entity_id,
                'tag_name': tag_name,
                'tag_value': tag_value,
                'created': now,
                'updated': now,
                'created_by': created_by or 'system',
                'updated_by': created_by or 'system'
            }
            
            logger.info("🔍 DEBUG: Tag data prepared: %s", tag_data)
            logger.info("🔍 DEBUG: Using table: %s", self.table_name)
            
            success = self.vast_db_manager.insert_record(self.table_name, tag_data)
            logger.info("🔍 DEBUG: insert_record returned: %s", success)
            
            if success:
                logger.info("✅ Created tag %s=%s for %s %s", tag_name, tag_value, entity_type, entity_id)
            else:
                logger.error("❌ Failed to create tag %s=%s for %s %s", tag_name, tag_value, entity_type, entity_id)
            
            return success
            
        except Exception as e:
            logger.error("Failed to create tag %s=%s for %s %s: %s", tag_name, tag_value, entity_type, entity_id, e)
            return False
    
    async def update_tag(self, entity_type: str, entity_id: str, tag_name: str, tag_value: str,
                        updated_by: Optional[str] = None) -> bool:
        """
        Update an existing tag for an entity
        
        Args:
            entity_type: Type of entity ('source' or 'flow')
            entity_id: ID of the entity
            tag_name: Name of the tag to update
            tag_value: New value for the tag
            updated_by: User who updated the tag
            
        Returns:
            bool: True if update successful, False otherwise
        """
        try:
            # Check if tag exists
            existing_tag = await self.get_tag(entity_type, entity_id, tag_name)
            if existing_tag is None:
                # Tag doesn't exist, create it
                return await self.create_tag(entity_type, entity_id, tag_name, tag_value, updated_by)
            
            # Update existing tag using VAST update method
            now = datetime.now(timezone.utc)
            update_data = {
                'tag_value': [tag_value],  # VastDBManager expects List[Any] format
                'updated': [now],          # VastDBManager expects List[Any] format
                'updated_by': [updated_by or 'system']  # VastDBManager expects List[Any] format
            }
            
            # Build predicate for update
            predicate = (_.entity_type == entity_type) & (_.entity_id == entity_id) & (_.tag_name == tag_name)
            
            # Use VAST update method
            success = self.vast_db_manager.update(self.table_name, update_data, predicate)
            if success:
                logger.info("Updated tag %s=%s for %s %s", tag_name, tag_value, entity_type, entity_id)
            else:
                logger.error("Failed to update tag %s=%s for %s %s", tag_name, tag_value, entity_type, entity_id)
            
            return success > 0  # update returns number of rows updated
            
        except Exception as e:
            logger.error("Failed to update tag %s=%s for %s %s: %s", tag_name, tag_value, entity_type, entity_id, e)
            return False
    
    async def update_tags(self, entity_type: str, entity_id: str, tags: Tags, 
                         updated_by: Optional[str] = None) -> bool:
        """
        Update all tags for an entity (replace existing tags)
        
        Args:
            entity_type: Type of entity ('source' or 'flow')
            entity_id: ID of the entity
            tags: Tags object containing all tags to set
            updated_by: User who updated the tags
            
        Returns:
            bool: True if update successful, False otherwise
        """
        try:
            logger.info("🔍 DEBUG: Starting update_tags for %s %s", entity_type, entity_id)
            logger.info("🔍 DEBUG: Tags to update: %s", tags.root if tags and tags.root else "None")
            
            if not tags or not tags.root:
                # No tags provided, delete all existing tags
                logger.info("🔍 DEBUG: No tags provided, deleting all existing tags")
                return await self.delete_all_tags(entity_type, entity_id)
            
            # First, delete all existing tags for this entity
            logger.info("🔍 DEBUG: Deleting existing tags for %s %s", entity_type, entity_id)
            delete_success = await self.delete_all_tags(entity_type, entity_id)
            if not delete_success:
                logger.error("❌ Failed to delete existing tags for %s %s", entity_type, entity_id)
                return False
            
            logger.info("🔍 DEBUG: Successfully deleted existing tags")
            
            # Create new tags
            success_count = 0
            total_tags = len(tags.root)
            logger.info("🔍 DEBUG: Creating %d new tags", total_tags)
            
            for tag_name, tag_value in tags.root.items():
                logger.info("🔍 DEBUG: Creating tag: %s=%s", tag_name, tag_value)
                if await self.create_tag(entity_type, entity_id, tag_name, tag_value, updated_by):
                    success_count += 1
                    logger.info("🔍 DEBUG: Tag %s created successfully (%d/%d)", tag_name, success_count, total_tags)
                else:
                    logger.error("🔍 DEBUG: Tag %s creation failed", tag_name)
            
            if success_count == total_tags:
                logger.info("✅ Successfully updated all %d tags for %s %s", success_count, entity_type, entity_id)
                return True
            else:
                logger.warning("⚠️ Partially updated tags for %s %s: %d/%d successful", 
                             entity_type, entity_id, success_count, total_tags)
                return False
            
        except Exception as e:
            logger.error("Failed to update tags for %s %s: %s", entity_type, entity_id, e)
            return False
    
    async def delete_tag(self, entity_type: str, entity_id: str, tag_name: str) -> bool:
        """
        Delete a specific tag for an entity
        
        Args:
            entity_type: Type of entity ('source' or 'flow')
            entity_id: ID of the entity
            tag_name: Name of the tag to delete
            
        Returns:
            bool: True if deletion successful, False otherwise
        """
        try:
            # Build predicate for deletion
            predicate = (_.entity_type == entity_type) & (_.entity_id == entity_id) & (_.tag_name == tag_name)
            
            # Use VAST delete method
            success = self.vast_db_manager.delete(self.table_name, predicate)
            if success >= 0:  # 0 or positive means success (0 means no rows to delete)
                logger.info("Deleted tag %s for %s %s (%d rows)", tag_name, entity_type, entity_id, success)
            else:
                logger.error("Failed to delete tag %s for %s %s", tag_name, entity_type, entity_id)
            
            return success >= 0  # 0 or positive means success
            
        except Exception as e:
            logger.error("Failed to delete tag %s for %s %s: %s", tag_name, entity_type, entity_id, e)
            return False
    
    async def delete_all_tags(self, entity_type: str, entity_id: str) -> bool:
        """
        Delete all tags for an entity
        
        Args:
            entity_type: Type of entity ('source' or 'flow')
            entity_id: ID of the entity
            
        Returns:
            bool: True if deletion successful, False otherwise
        """
        try:
            # Build predicate for deletion
            predicate = (_.entity_type == entity_type) & (_.entity_id == entity_id)
            
            # Use VAST delete method
            success = self.vast_db_manager.delete(self.table_name, predicate)
            if success >= 0:  # 0 or positive means success (0 means no rows to delete)
                logger.info("Deleted all tags for %s %s (%d rows)", entity_type, entity_id, success)
            else:
                logger.error("Failed to delete all tags for %s %s", entity_type, entity_id)
            
            return success >= 0  # 0 or positive means success
            
        except Exception as e:
            logger.error("Failed to delete all tags for %s %s: %s", entity_type, entity_id, e)
            return False
    
    async def search_tags(self, entity_type: Optional[str] = None, tag_name: Optional[str] = None, 
                         tag_value: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Search for tags based on criteria
        
        Args:
            entity_type: Filter by entity type ('source' or 'flow')
            tag_name: Filter by tag name
            tag_value: Filter by tag value
            
        Returns:
            List of tag records matching the criteria
        """
        try:
            # Build VAST predicate for search
            predicate = None
            conditions = []
            
            if entity_type:
                conditions.append(_.entity_type == entity_type)
            if tag_name:
                conditions.append(_.tag_name == tag_name)
            if tag_value:
                conditions.append(_.tag_value == tag_value)
            
            if conditions:
                if len(conditions) == 1:
                    predicate = conditions[0]
                else:
                    predicate = conditions[0]
                    for condition in conditions[1:]:
                        predicate = predicate & condition
            
            # Query tags table using VAST select method
            result = self.vast_db_manager.select(
                self.table_name, 
                predicate=predicate, 
                output_by_row=True
            )
            
            return result if result else []
            
        except Exception as e:
            logger.error("Failed to search tags: %s", e)
            return []
    
    async def get_tag_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about tags usage
        
        Returns:
            Dictionary containing tag statistics
        """
        try:
            # Get all tags for statistics
            all_tags = self.vast_db_manager.select(
                self.table_name, 
                predicate=None, 
                output_by_row=True
            )
            
            if not all_tags:
                return {
                    'total_tags': 0,
                    'entity_counts': {},
                    'unique_tag_names': 0
                }
            
            # Calculate statistics
            total_tags = len(all_tags)
            entity_counts = {}
            unique_tag_names = set()
            
            for tag in all_tags:
                entity_type = tag.get('entity_type', 'unknown')
                entity_counts[entity_type] = entity_counts.get(entity_type, 0) + 1
                unique_tag_names.add(tag.get('tag_name', ''))
            
            return {
                'total_tags': total_tags,
                'entity_counts': entity_counts,
                'unique_tag_names': len(unique_tag_names)
            }
            
        except Exception as e:
            logger.error("Failed to get tag statistics: %s", e)
            return {}
