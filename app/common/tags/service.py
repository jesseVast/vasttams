"""
Generic Tag Storage Service

This module handles all tag-related storage operations for any entity type.
It provides a generic interface for tag management that works with sources,
flows, or any future entity types.

TAMS 8.0: Supports both string and array tag values.
"""

import logging
import uuid
import json
from typing import Optional, Dict, Any, List, Tuple, Union

from .tag_manager import get_tag_manager, validate_tags, standardize_tags
from ..models import Tags
from ..storage.timestamp_utils import get_tams_timestamp, prepare_data_for_pyarrow

logger = logging.getLogger(__name__)


class TagStorageService:
    """Generic tag storage service that handles tags for any entity type"""
    
    def __init__(self, vast_db, s3_client):
        self.vast_db = vast_db
        self.s3_client = s3_client
    
    async def get_entity_tags(self, entity_type: str, entity_id: str) -> Optional[Tags]:
        """Get tags for any entity type"""
        try:
            tags_table = self.vast_db.get_qualified_table_name("tags")
            
            sql = f"""
            SELECT tag_name, tag_value 
            FROM {tags_table} 
            WHERE entity_type = '{entity_type}' AND entity_id = '{entity_id}'
            ORDER BY tag_name
            """
            result = self.vast_db.execute_sql(sql)
            logger.debug("SQL result for get_entity_tags: %s", result)
            
            if result and result.get('data'):
                tags_dict = {}
                for row in result['data']:
                    if isinstance(row, dict) and 'tag_name' in row and 'tag_value' in row:
                        tag_name = row['tag_name']
                        tag_value = row['tag_value']
                        
                        # TAMS 8.0: Parse array values from JSON if present
                        if isinstance(tag_value, str):
                            # Try to parse as JSON array
                            try:
                                parsed = json.loads(tag_value)
                                if isinstance(parsed, list):
                                    tags_dict[tag_name] = parsed  # Array value
                                else:
                                    tags_dict[tag_name] = tag_value  # String value
                            except (json.JSONDecodeError, ValueError):
                                tags_dict[tag_name] = tag_value  # String value
                        elif isinstance(tag_value, list):
                            tags_dict[tag_name] = tag_value  # Already an array
                        else:
                            tags_dict[tag_name] = tag_value  # Other type
                    else:
                        logger.warning("Unexpected row format: %s", row)
                return Tags(tags_dict) if tags_dict else None
            return None
        except Exception as e:
            logger.error("Failed to get tags for %s %s: %s", entity_type, entity_id, e)
            raise e
    
    async def update_entity_tags(self, entity_type: str, entity_id: str, tags: Tags) -> bool:
        """Update tags for any entity type with validation and standardization"""
        try:
            # Validate and standardize tags
            if tags and tags.root:
                is_valid, errors = validate_tags(tags.root)
                if not is_valid:
                    logger.warning("Tag validation failed for %s %s: %s", entity_type, entity_id, errors)
                    raise ValueError(f"Invalid tags: {'; '.join(errors)}")
                
                # Standardize tags
                standardized_tags = standardize_tags(tags.root)
                tags = Tags(standardized_tags)
            
            # Convert tags to separate table approach
            tags_dict = tags.root if tags and tags.root else {}
            
            # First, delete existing tags for this entity
            tags_table = self.vast_db.get_qualified_table_name("tags")
            delete_sql = f"DELETE FROM {tags_table} WHERE entity_type = '{entity_type}' AND entity_id = '{entity_id}'"
            self.vast_db.execute_sql(delete_sql)
            
            # Then, insert new tags
            if tags_dict:
                now = get_tams_timestamp()
                
                for tag_name, tag_value in tags_dict.items():
                    tag_id = str(uuid.uuid4())
                    
                    # TAMS 8.0: Serialize array values to JSON
                    if isinstance(tag_value, list):
                        tag_value_str = json.dumps(tag_value)
                    else:
                        tag_value_str = tag_value
                    
                    tag_data = {
                        'id': tag_id,
                        'entity_type': entity_type,
                        'entity_id': entity_id,
                        'tag_name': tag_name,
                        'tag_value': tag_value_str,
                        'created_at': now,
                        'updated_at': now,
                        'created_date': now,
                        'updated_date': now,
                        'deleted_date': None
                    }
                    
                    # Convert timestamp fields to PyArrow format
                    tag_data = prepare_data_for_pyarrow(tag_data)
                    
                    # Use insert_record instead of execute_sql
                    self.vast_db.insert_record("tags", tag_data)
            
            return True
        except Exception as e:
            logger.error("Failed to update tags for %s %s: %s", entity_type, entity_id, e)
            raise e
    
    async def get_entity_tag(self, entity_type: str, entity_id: str, name: str) -> Optional[str]:
        """Get a specific tag for any entity type"""
        try:
            tags = await self.get_entity_tags(entity_type, entity_id)
            if tags and hasattr(tags, 'root') and tags.root:
                return tags.root.get(name)
            return None
        except Exception as e:
            logger.error("Failed to get tag %s for %s %s: %s", name, entity_type, entity_id, e)
            raise e
    
    async def update_entity_tag(self, entity_type: str, entity_id: str, name: str, value: str) -> bool:
        """Update a specific tag for any entity type"""
        try:
            # Get current tags
            current_tags = await self.get_entity_tags(entity_type, entity_id)
            if not current_tags:
                current_tags = Tags({})
            
            # Update the specific tag in the root dictionary
            if not current_tags.root:
                current_tags.root = {}
            current_tags.root[name] = value
            
            # Save updated tags
            return await self.update_entity_tags(entity_type, entity_id, current_tags)
        except Exception as e:
            logger.error("Failed to update tag %s for %s %s: %s", name, entity_type, entity_id, e)
            raise e
    
    async def delete_entity_tag(self, entity_type: str, entity_id: str, name: str) -> bool:
        """Delete a specific tag for any entity type"""
        try:
            # Get current tags
            current_tags = await self.get_entity_tags(entity_type, entity_id)
            if not current_tags or not current_tags.root or name not in current_tags.root:
                return False
            
            # Remove the specific tag from the root dictionary
            del current_tags.root[name]
            
            # Save updated tags
            return await self.update_entity_tags(entity_type, entity_id, current_tags)
        except Exception as e:
            logger.error("Failed to delete tag %s for %s %s: %s", name, entity_type, entity_id, e)
            raise e
    
    # Convenience methods for backward compatibility
    async def get_source_tags(self, source_id: str) -> Optional[Tags]:
        """Get source tags - convenience method"""
        return await self.get_entity_tags("source", source_id)
    
    async def update_source_tags(self, source_id: str, tags: Tags) -> bool:
        """Update source tags - convenience method"""
        return await self.update_entity_tags("source", source_id, tags)
    
    async def get_source_tag(self, source_id: str, name: str) -> Optional[str]:
        """Get a specific source tag - convenience method"""
        return await self.get_entity_tag("source", source_id, name)
    
    async def update_source_tag(self, source_id: str, name: str, value: str) -> bool:
        """Update a specific source tag - convenience method"""
        return await self.update_entity_tag("source", source_id, name, value)
    
    async def delete_source_tag(self, source_id: str, name: str) -> bool:
        """Delete a specific source tag - convenience method"""
        return await self.delete_entity_tag("source", source_id, name)
    
    async def get_flow_tags(self, flow_id: str) -> Optional[Tags]:
        """Get flow tags - convenience method"""
        return await self.get_entity_tags("flow", flow_id)
    
    async def update_flow_tags(self, flow_id: str, tags: Tags) -> bool:
        """Update flow tags - convenience method"""
        return await self.update_entity_tags("flow", flow_id, tags)
    
    async def update_flow_tag(self, flow_id: str, name: str, value: str) -> bool:
        """Update a specific flow tag - convenience method"""
        return await self.update_entity_tag("flow", flow_id, name, value)
    
    async def delete_flow_tag(self, flow_id: str, name: str) -> bool:
        """Delete a specific flow tag - convenience method"""
        return await self.delete_entity_tag("flow", flow_id, name)
    
    # Enhanced tag querying and analytics methods
    
    async def query_entities_by_tags(self, entity_type: str, tag_filters: Dict[str, Any], limit: int = 100) -> List[Dict[str, Any]]:
        """Query entities by tag filters using SQL queries"""
        try:
            from .tag_manager import generate_sql_query_for_tags
            
            # Get qualified table name
            table_name = self.vast_db.get_qualified_table_name(entity_type + "s")
            
            # Generate SQL query for tags
            sql_query = generate_sql_query_for_tags(table_name, tag_filters, "*", limit)
            logger.debug("Generated SQL tag query: %s", sql_query)
            
            # Execute SQL query
            result = self.vast_db.execute_sql(sql_query)
            
            # Parse results
            entities = []
            if isinstance(result, dict) and 'data' in result:
                entities = [dict(row) for row in result['data']]
            elif isinstance(result, list):
                entities = [dict(row) for row in result]
            
            return entities
        except Exception as e:
            logger.error("Failed to query %s by tags: %s", entity_type, e)
            raise e
    
    # Convenience methods for backward compatibility
    async def query_sources_by_tags(self, tag_filters: Dict[str, Any], limit: int = 100) -> List[Dict[str, Any]]:
        """Query sources by tag filters - convenience method"""
        return await self.query_entities_by_tags("source", tag_filters, limit)
    
    async def query_flows_by_tags(self, tag_filters: Dict[str, Any], limit: int = 100) -> List[Dict[str, Any]]:
        """Query flows by tag filters - convenience method"""
        return await self.query_entities_by_tags("flow", tag_filters, limit)
    
    async def get_tag_analytics(self, entity_type: str = "sources") -> Dict[str, Any]:
        """Get tag usage analytics for any entity type"""
        try:
            # Get all entities with tags
            result = self.vast_db.query(entity_type + "s").select("id, tags").execute()
            
            # Parse results
            entities = []
            if isinstance(result, list):
                entities = [dict(row) for row in result]
            elif isinstance(result, dict) and 'data' in result:
                entities = [dict(row) for row in result['data']]
            
            # Extract tags data
            tags_data = []
            for entity in entities:
                if entity.get('tags'):
                    try:
                        tags_dict = entity['tags']
                        # Handle PyArrow Map type - convert to dictionary
                        if isinstance(tags_dict, dict):
                            # Already a dictionary (PyArrow Map converted to dict)
                            pass
                        elif isinstance(tags_dict, str):
                            # Fallback for JSON string (backward compatibility)
                            import json
                            tags_dict = json.loads(tags_dict)
                        else:
                            # Handle PyArrow Map object
                            tags_dict = dict(tags_dict) if hasattr(tags_dict, '__iter__') else {}
                        
                        if isinstance(tags_dict, dict):
                            tags_data.append(tags_dict)
                    except (TypeError, ValueError, json.JSONDecodeError):
                        continue
            
            # Generate analytics using tag manager
            tag_manager = get_tag_manager()
            analytics = tag_manager.get_tag_analytics(tags_data)
            analytics['entity_type'] = entity_type
            analytics['total_entities'] = len(entities)
            
            return analytics
        except Exception as e:
            logger.error("Failed to get tag analytics for %s: %s", entity_type, e)
            raise e
    
    async def get_standardized_tags(self) -> Dict[str, Any]:
        """Get standardized tag definitions"""
        try:
            tag_manager = get_tag_manager()
            standardized_tags = tag_manager.get_standardized_tags()
            
            # Convert to serializable format
            result = {}
            for name, definition in standardized_tags.items():
                result[name] = {
                    "name": definition.name,
                    "description": definition.description,
                    "data_type": definition.data_type,
                    "required": definition.required,
                    "allowed_values": definition.allowed_values,
                    "pattern": definition.pattern,
                    "examples": definition.examples,
                    "deprecated": definition.deprecated,
                    "replacement": definition.replacement
                }
            
            return result
        except Exception as e:
            logger.error("Failed to get standardized tags: %s", e)
            raise e
    
    async def create_tag_proposal(self, name: str, description: str, data_type: str,
                                justification: str, examples: List[str], proposed_by: str) -> Dict[str, Any]:
        """Create a new tag proposal"""
        try:
            tag_manager = get_tag_manager()
            proposal = tag_manager.create_tag_proposal(
                name=name,
                description=description,
                data_type=data_type,
                justification=justification,
                examples=examples,
                proposed_by=proposed_by
            )
            
            return {
                "name": proposal.name,
                "description": proposal.description,
                "data_type": proposal.data_type,
                "justification": proposal.justification,
                "examples": proposal.examples,
                "proposed_by": proposal.proposed_by,
                "proposed_at": proposal.proposed_at.isoformat(),
                "status": proposal.status
            }
        except Exception as e:
            logger.error("Failed to create tag proposal: %s", e)
            raise e