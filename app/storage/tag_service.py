"""
Tag Storage Service

This module handles all tag-related storage operations including
CRUD operations for source tags and tag management.
"""

import logging
from typing import Optional, Dict, Any, List, Tuple

from fastapi import HTTPException
from .interfaces import StorageInterface
from .tag_manager import get_tag_manager, validate_tags, standardize_tags
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
            
            # Handle PyArrow Map type - convert to dictionary
            if tags_data is not None:
                if isinstance(tags_data, dict):
                    # Already a dictionary (PyArrow Map converted to dict)
                    pass
                elif isinstance(tags_data, str):
                    # Fallback for JSON string (backward compatibility)
                    import json
                    try:
                        tags_data = json.loads(tags_data)
                    except (json.JSONDecodeError, TypeError):
                        tags_data = None
                else:
                    # Handle PyArrow Map object
                    try:
                        tags_data = dict(tags_data) if hasattr(tags_data, '__iter__') else None
                    except (TypeError, ValueError):
                        tags_data = None
            
            return Tags(tags_data) if tags_data else None
        except Exception as e:
            logger.error("Failed to get source tags for %s: %s", source_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def update_source_tags(self, source_id: str, tags: Tags) -> bool:
        """Update source tags with validation and standardization"""
        try:
            # Validate and standardize tags
            if tags and tags.root:
                is_valid, errors = validate_tags(tags.root)
                if not is_valid:
                    logger.warning("Tag validation failed for source %s: %s", source_id, errors)
                    raise HTTPException(status_code=400, detail=f"Invalid tags: {'; '.join(errors)}")
                
                # Standardize tags
                standardized_tags = standardize_tags(tags.root)
                tags = Tags(standardized_tags)
            
            # Update the source with new tags - store as PyArrow Map
            tags_dict = tags.root if tags and tags.root else {}
            self.vast_db.query("sources").update().set(tags=tags_dict).where(f"id = '{source_id}'").execute()
            return True
        except HTTPException:
            raise
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
            
            # Handle PyArrow Map type - convert to dictionary
            if isinstance(tags_data, dict):
                # Already a dictionary (PyArrow Map converted to dict)
                tags_dict = tags_data
            elif isinstance(tags_data, str):
                # Fallback for JSON string (backward compatibility)
                import json
                try:
                    tags_dict = json.loads(tags_data)
                except (json.JSONDecodeError, TypeError):
                    return None
            elif isinstance(tags_data, list):
                # Handle case where tags is returned as a list
                if len(tags_data) == 1 and tags_data[0] is None:
                    return None
                tags_dict = tags_data[0] if tags_data else {}
            else:
                # Handle PyArrow Map object
                try:
                    tags_dict = dict(tags_data) if hasattr(tags_data, '__iter__') else {}
                except (TypeError, ValueError):
                    return None
            
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
        """Update flow tags with validation and standardization"""
        try:
            # Validate and standardize tags
            if tags and tags.root:
                is_valid, errors = validate_tags(tags.root)
                if not is_valid:
                    logger.warning("Tag validation failed for flow %s: %s", flow_id, errors)
                    raise HTTPException(status_code=400, detail=f"Invalid tags: {'; '.join(errors)}")
                
                # Standardize tags
                standardized_tags = standardize_tags(tags.root)
                tags = Tags(standardized_tags)
            
            import asyncio
            tags_dict = tags.root if tags and tags.root else {}
            logger.debug("Updating flow %s tags with Map: %s", flow_id, tags_dict)
            
            result = self.vast_db.query("flows").update().set(tags=tags_dict).where(f"id = '{flow_id}'").execute()
            logger.debug("Update query result for flow %s: %s", flow_id, result)
            
            # Add a small delay to allow the update to be committed
            await asyncio.sleep(0.1)
            
            return True
        except HTTPException:
            raise
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
    
    # Enhanced tag querying and analytics methods
    
    async def query_sources_by_tags(self, tag_filters: Dict[str, Any], limit: int = 100) -> List[Dict[str, Any]]:
        """Query sources by tag filters using SQL queries for Map types"""
        try:
            from .tag_manager import generate_sql_query_for_tags
            
            # Get qualified table name
            table_name = self.vast_db.get_qualified_table_name("sources")
            
            # Generate SQL query for tags
            sql_query = generate_sql_query_for_tags(table_name, tag_filters, "*", limit)
            logger.debug("Generated SQL tag query: %s", sql_query)
            
            # Execute SQL query
            result = self.vast_db.execute_sql(sql_query)
            
            # Parse results
            sources = []
            if isinstance(result, dict) and 'data' in result:
                sources = [dict(row) for row in result['data']]
            elif isinstance(result, list):
                sources = [dict(row) for row in result]
            
            return sources
        except Exception as e:
            logger.error("Failed to query sources by tags: %s", e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def query_flows_by_tags(self, tag_filters: Dict[str, Any], limit: int = 100) -> List[Dict[str, Any]]:
        """Query flows by tag filters using SQL queries for Map types"""
        try:
            from .tag_manager import generate_sql_query_for_tags
            
            # Get qualified table name
            table_name = self.vast_db.get_qualified_table_name("flows")
            
            # Generate SQL query for tags
            sql_query = generate_sql_query_for_tags(table_name, tag_filters, "*", limit)
            logger.debug("Generated SQL tag query: %s", sql_query)
            
            # Execute SQL query
            result = self.vast_db.execute_sql(sql_query)
            
            # Parse results
            flows = []
            if isinstance(result, dict) and 'data' in result:
                flows = [dict(row) for row in result['data']]
            elif isinstance(result, list):
                flows = [dict(row) for row in result]
            
            return flows
        except Exception as e:
            logger.error("Failed to query flows by tags: %s", e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def get_tag_analytics(self, entity_type: str = "sources") -> Dict[str, Any]:
        """Get tag usage analytics for sources or flows"""
        try:
            # Get all entities with tags
            if entity_type == "sources":
                result = self.vast_db.query("sources").select("id, tags").execute()
            else:
                result = self.vast_db.query("flows").select("id, tags").execute()
            
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
            raise HTTPException(status_code=500, detail="Internal server error")
    
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
            raise HTTPException(status_code=500, detail="Internal server error")
    
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
            raise HTTPException(status_code=500, detail="Internal server error")