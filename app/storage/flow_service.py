"""
Flow Storage Service

This module handles all flow-related storage operations including
CRUD operations, filtering, and flow management.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

from fastapi import HTTPException
from .interfaces import StorageInterface
from .timestamp_utils import get_tams_timestamp, get_timeline_synchronizer
from ..models import Flow, FlowFilters, FlowDetailFilters, VideoFlow, AudioFlow, ImageFlow, DataFlow, MultiFlow, Source

logger = logging.getLogger(__name__)


def _get_flow_class(format_str: str):
    """Get the appropriate flow class based on format"""
    if format_str == "urn:x-nmos:format:video":
        return VideoFlow
    elif format_str == "urn:x-nmos:format:audio":
        return AudioFlow
    elif format_str == "urn:x-nmos:format:image":
        return ImageFlow
    elif format_str == "urn:x-nmos:format:data":
        return DataFlow
    elif format_str == "urn:x-nmos:format:multi":
        return MultiFlow
    else:
        # Default to VideoFlow for unknown formats
        return VideoFlow


class FlowStorageService:
    """Handles flow-related storage operations"""
    
    def __init__(self, vast_db, s3_client):
        self.vast_db = vast_db
        self.s3_client = s3_client
    
    async def get_flows(self, filters: FlowFilters) -> List[Flow]:
        """Get flows with filtering"""
        try:
            # Build query using vaststore
            query = self.vast_db.query("flows").select("*")
            
            # Add filters
            if filters.source_id:
                query = query.where(f"source_id = '{filters.source_id}'")
            if filters.label:
                query = query.where(f"label = '{filters.label}'")
            if filters.format:
                query = query.where(f"format = '{filters.format}'")
            
            # Add limit
            if filters.limit:
                query = query.limit(filters.limit)
            
            result = query.execute()
            
            # Convert to Flow objects
            flows = []
            # VAST returns a dict with 'data' field containing column arrays
            if isinstance(result, dict) and 'data' in result:
                data = result['data']
                if isinstance(data, dict) and data:
                    # Convert column arrays to row dictionaries
                    num_rows = len(next(iter(data.values())))
                    for i in range(num_rows):
                        flow_data = {}
                        for column, values in data.items():
                            if column != '$row_id':  # Skip internal row IDs
                                value = values[i] if i < len(values) else None
                                # Parse JSON fields
                                if column in ['essence_parameters', 'tags'] and isinstance(value, str):
                                    try:
                                        import json
                                        flow_data[column] = json.loads(value)
                                    except (json.JSONDecodeError, TypeError):
                                        flow_data[column] = value
                                else:
                                    flow_data[column] = value
                        # Get the appropriate flow class based on format
                        flow_class = _get_flow_class(flow_data.get('format', 'urn:x-nmos:format:video'))
                        flows.append(flow_class(**flow_data))
                elif isinstance(data, list):
                    # If data is a list, iterate directly
                    for row in data:
                        flow_data = dict(row) if hasattr(row, '__iter__') and not isinstance(row, str) else row
                        # Parse JSON fields
                        for field in ['essence_parameters', 'tags']:
                            if field in flow_data and isinstance(flow_data[field], str):
                                try:
                                    import json
                                    flow_data[field] = json.loads(flow_data[field])
                                except (json.JSONDecodeError, TypeError):
                                    pass
                        # Get the appropriate flow class based on format
                        flow_class = _get_flow_class(flow_data.get('format', 'urn:x-nmos:format:video'))
                        flows.append(flow_class(**flow_data))
            else:
                # Fallback for direct list results
                for row in result:
                    flow_data = dict(row) if hasattr(row, '__iter__') and not isinstance(row, str) else row
                    # Parse JSON fields
                    for field in ['essence_parameters', 'tags']:
                        if field in flow_data and isinstance(flow_data[field], str):
                            try:
                                import json
                                flow_data[field] = json.loads(flow_data[field])
                            except (json.JSONDecodeError, TypeError):
                                pass
                    # Get the appropriate flow class based on format
                    flow_class = _get_flow_class(flow_data.get('format', 'urn:x-nmos:format:video'))
                    flows.append(flow_class(**flow_data))
            
            return flows
        except Exception as e:
            logger.error("Failed to get flows: %s", e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def get_flow(self, flow_id: str) -> Optional[Flow]:
        """Get a specific flow by ID"""
        try:
            result = self.vast_db.query("flows").select("*").where(f"id = '{flow_id}'").execute()
            
            # Handle VAST query result format
            if isinstance(result, dict) and 'data' in result:
                data = result['data']
                if isinstance(data, dict) and data:
                    # Convert column arrays to row dictionaries
                    num_rows = len(next(iter(data.values())))
                    if num_rows == 0:
                        return None
                    
                    # Get the first row
                    flow_data = {}
                    for column, values in data.items():
                        if column != '$row_id':  # Skip internal row IDs
                            value = values[0] if len(values) > 0 else None
                            # Parse JSON fields
                            if column in ['essence_parameters', 'tags'] and isinstance(value, str):
                                try:
                                    import json
                                    flow_data[column] = json.loads(value)
                                except (json.JSONDecodeError, TypeError):
                                    flow_data[column] = value
                            else:
                                flow_data[column] = value
                    # Get the appropriate flow class based on format
                    flow_class = _get_flow_class(flow_data.get('format', 'urn:x-nmos:format:video'))
                    return flow_class(**flow_data)
                elif isinstance(data, list):
                    if not data:
                        return None
                    flow_data = dict(data[0]) if hasattr(data[0], '__iter__') and not isinstance(data[0], str) else data[0]
                    # Parse JSON fields
                    for field in ['essence_parameters', 'tags']:
                        if field in flow_data and isinstance(flow_data[field], str):
                            try:
                                import json
                                flow_data[field] = json.loads(flow_data[field])
                            except (json.JSONDecodeError, TypeError):
                                pass
                    # Get the appropriate flow class based on format
                    flow_class = _get_flow_class(flow_data.get('format', 'urn:x-nmos:format:video'))
                    return flow_class(**flow_data)
            else:
                if not result or len(result) == 0:
                    return None
                flow_data = dict(result[0]) if hasattr(result[0], '__iter__') and not isinstance(result[0], str) else result[0]
                # Parse JSON fields
                if 'essence_parameters' in flow_data and isinstance(flow_data['essence_parameters'], str):
                    try:
                        import json
                        flow_data['essence_parameters'] = json.loads(flow_data['essence_parameters'])
                    except (json.JSONDecodeError, TypeError):
                        pass
                # Get the appropriate flow class based on format
                flow_class = _get_flow_class(flow_data.get('format', 'urn:x-nmos:format:video'))
                return flow_class(**flow_data)
        except Exception as e:
            logger.error("Failed to get flow %s: %s", flow_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def create_flow(self, flow: Flow) -> bool:
        """Create a new flow"""
        try:
            now = get_tams_timestamp()
            flow.created = now
            flow.metadata_updated = now
            flow.segments_updated = now
            
            # Check if source exists, create it automatically if it doesn't
            await self._ensure_source_exists(flow)
            
            flow_data = flow.model_dump()
            
            # Convert timestamp fields to PyArrow format using centralized function
            from app.storage.timestamp_utils import prepare_data_for_pyarrow
            flow_data = prepare_data_for_pyarrow(flow_data)
            
            logger.debug("Creating flow with data: %s", flow_data)
            result = self.vast_db.insert_record("flows", flow_data)
            logger.debug("Flow creation result: %s", result)
            logger.debug("Flow created successfully with ID: %s", flow.id)
            return True
        except Exception as e:
            logger.error("Failed to create flow: %s", e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def update_flow(self, flow_id: str, flow: Flow) -> bool:
        """Update an existing flow"""
        try:
            flow.metadata_updated = get_tams_timestamp()
            
            # Only update mutable fields, exclude read-only fields
            flow_data = flow.model_dump(exclude={'id', 'created', 'created_by', 'collected_by'})
            
            # Convert timestamp fields to SQL format for query builder using centralized function
            from app.storage.timestamp_utils import prepare_data_for_sql
            flow_data = prepare_data_for_sql(flow_data)
            
            # Convert Tags object to JSON string for database compatibility
            if 'tags' in flow_data and flow_data['tags'] is not None:
                import json
                if hasattr(flow_data['tags'], 'root'):
                    flow_data['tags'] = json.dumps(flow_data['tags'].root)
                elif isinstance(flow_data['tags'], dict):
                    flow_data['tags'] = json.dumps(flow_data['tags'])
                # If it's already a string, leave it as is
            
            # Convert essence_parameters to JSON string for database compatibility
            if 'essence_parameters' in flow_data and flow_data['essence_parameters'] is not None:
                import json
                if hasattr(flow_data['essence_parameters'], 'model_dump'):
                    flow_data['essence_parameters'] = json.dumps(flow_data['essence_parameters'].model_dump())
                elif isinstance(flow_data['essence_parameters'], dict):
                    flow_data['essence_parameters'] = json.dumps(flow_data['essence_parameters'])
            
            # Convert flow_collection to JSON string for database compatibility
            if 'flow_collection' in flow_data and flow_data['flow_collection'] is not None:
                import json
                if hasattr(flow_data['flow_collection'], 'root'):
                    flow_data['flow_collection'] = json.dumps(flow_data['flow_collection'].root)
                elif isinstance(flow_data['flow_collection'], list):
                    flow_data['flow_collection'] = json.dumps(flow_data['flow_collection'])
            
            # Filter out None values to avoid "unknown" type errors
            flow_data = {k: v for k, v in flow_data.items() if v is not None}
            
            # Use query builder with proper timestamp handling
            self.vast_db.query("flows").update().set(**flow_data).where(f"id = '{flow_id}'").execute()
            return True
        except Exception as e:
            logger.error("Failed to update flow %s: %s", flow_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def update_flow_description(self, flow_id: str, description: str) -> bool:
        """Update flow description only"""
        try:
            self.vast_db.query("flows").update().set(description=description).where(f"id = '{flow_id}'").execute()
            return True
        except Exception as e:
            logger.error("Failed to update flow description %s: %s", flow_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def delete_flow_description(self, flow_id: str) -> bool:
        """Delete flow description only"""
        try:
            self.vast_db.query("flows").update().set(description=None).where(f"id = '{flow_id}'").execute()
            return True
        except Exception as e:
            logger.error("Failed to delete flow description %s: %s", flow_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def update_flow_label(self, flow_id: str, label: str) -> bool:
        """Update flow label only"""
        try:
            self.vast_db.query("flows").update().set(label=label).where(f"id = '{flow_id}'").execute()
            return True
        except Exception as e:
            logger.error("Failed to update flow label %s: %s", flow_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def delete_flow_label(self, flow_id: str) -> bool:
        """Delete flow label only"""
        try:
            self.vast_db.query("flows").update().set(label=None).where(f"id = '{flow_id}'").execute()
            return True
        except Exception as e:
            logger.error("Failed to delete flow label %s: %s", flow_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def update_flow_read_only(self, flow_id: str, read_only: bool) -> bool:
        """Update flow read_only status only"""
        try:
            self.vast_db.query("flows").update().set(read_only=read_only).where(f"id = '{flow_id}'").execute()
            return True
        except Exception as e:
            logger.error("Failed to update flow read_only %s: %s", flow_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def delete_flow(self, flow_id: str, cascade: bool = True) -> bool:
        """Delete a flow"""
        try:
            # Delete flow segments first if cascade is True
            if cascade:
                await self._delete_flow_segments(flow_id)
            
            # Delete flow
            self.vast_db.query("flows").delete().where(f"id = '{flow_id}'").execute()
            return True
        except Exception as e:
            logger.error("Failed to delete flow %s: %s", flow_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def check_flow_read_only(self, flow_id: str) -> bool:
        """Check if a flow is read-only"""
        try:
            result = self.vast_db.query("flows").select("read_only").where(f"id = '{flow_id}'").execute()
            if not result or len(result) == 0:
                return False
            
            return result[0].get('read_only', False)
        except Exception as e:
            logger.error("Failed to check flow read-only status for %s: %s", flow_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def _delete_flow_segments(self, flow_id: str) -> bool:
        """Delete flow segments for a flow"""
        try:
            self.vast_db.query("segments").delete().where(f"flow_id = '{flow_id}'").execute()
            return True
        except Exception as e:
            logger.error("Failed to delete flow segments for %s: %s", flow_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def get_flow_with_source_details(self, flow_id: str) -> Optional[Dict[str, Any]]:
        """Get flow details with source information using join query"""
        try:
            flows_table = self.vast_db.get_qualified_table_name("flows")
            sources_table = self.vast_db.get_qualified_table_name("sources")
            
            sql = f"""
                SELECT 
                    f.id,
                    f.source_id,
                    f.format,
                    f.label,
                    f.description,
                    f.read_only,
                    f.created,
                    f.updated,
                    f.tags,
                    s.label as source_label,
                    s.format as source_format,
                    s.description as source_description
                FROM {flows_table} f
                JOIN {sources_table} s ON f.source_id = s.id
                WHERE f.id = '{flow_id}'
            """
            
            result = self.vast_db.execute_sql(sql)
            if result and 'data' in result and len(result['data']) > 0:
                row = result['data'][0]
                return {
                    "id": row[0],
                    "source_id": row[1],
                    "format": row[2],
                    "label": row[3],
                    "description": row[4],
                    "read_only": row[5],
                    "created": row[6],
                    "updated": row[7],
                    "tags": row[8],
                    "source": {
                        "id": row[1],
                        "label": row[9],
                        "format": row[10],
                        "description": row[11]
                    }
                }
            return None
        except Exception as e:
            logger.error("Failed to get flow with source details for %s: %s", flow_id, e)
            return None
    
    async def get_flows_with_source_details(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Get flows with source information using join query"""
        try:
            flows_table = self.vast_db.get_qualified_table_name("flows")
            sources_table = self.vast_db.get_qualified_table_name("sources")
            
            sql = f"""
                SELECT 
                    f.id,
                    f.source_id,
                    f.format,
                    f.label,
                    f.description,
                    f.read_only,
                    f.created,
                    f.updated,
                    f.tags,
                    s.label as source_label,
                    s.format as source_format,
                    s.description as source_description
                FROM {flows_table} f
                JOIN {sources_table} s ON f.source_id = s.id
            """
            
            # Add filters if provided
            where_conditions = []
            if filters:
                if filters.get("source_id"):
                    where_conditions.append(f"f.source_id = '{filters['source_id']}'")
                if filters.get("label"):
                    where_conditions.append(f"f.label = '{filters['label']}'")
                if filters.get("format"):
                    where_conditions.append(f"f.format = '{filters['format']}'")
                if filters.get("source_format"):
                    where_conditions.append(f"s.format = '{filters['source_format']}'")
            
            if where_conditions:
                sql += " WHERE " + " AND ".join(where_conditions)
            
            sql += " ORDER BY f.created DESC"
            
            result = self.vast_db.execute_sql(sql)
            if result and 'data' in result:
                flows = []
                for row in result['data']:
                    flows.append({
                        "id": row[0],
                        "source_id": row[1],
                        "format": row[2],
                        "label": row[3],
                        "description": row[4],
                        "read_only": row[5],
                        "created": row[6],
                        "updated": row[7],
                        "tags": row[8],
                        "source": {
                            "id": row[1],
                            "label": row[9],
                            "format": row[10],
                            "description": row[11]
                        }
                    })
                return flows
            return []
        except Exception as e:
            logger.error("Failed to get flows with source details: %s", e)
            return []
    
    async def _ensure_source_exists(self, flow: Flow) -> None:
        """Ensure source exists, create it automatically if it doesn't"""
        try:
            # Check if source exists
            source_query = self.vast_db.query("sources").select("*").where(f"id = '{flow.source_id}'")
            result = source_query.execute()
            
            if not result or not result.get('data') or len(result['data']) == 0:
                # Source doesn't exist, create it automatically
                logger.info("Source %s doesn't exist, creating it automatically", flow.source_id)
                
                # Create source with metadata from flow
                source = Source(
                    id=flow.source_id,
                    format=flow.format,
                    label=flow.label,
                    description=flow.description,
                    created_by=flow.created_by,
                    updated_by=flow.updated_by,
                    tags=flow.tags  # Replicate tags from flow to source
                )
                
                # Insert source into database
                source_data = source.model_dump(exclude={'source_collection', 'collected_by'})
                source_data['created'] = get_tams_timestamp()
                source_data['updated'] = get_tams_timestamp()
                
                self.vast_db.insert_record("sources", source_data)
                logger.info("Successfully created source %s with metadata from flow", flow.source_id)
            else:
                logger.debug("Source %s already exists", flow.source_id)
                
        except Exception as e:
            logger.error("Failed to ensure source exists for flow %s: %s", flow.id, e)
            raise HTTPException(status_code=500, detail="Failed to create source automatically")
